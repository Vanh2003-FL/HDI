from odoo import models, fields, api

class StockInventory(models.Model):
    _inherit = 'stock.quant'
    
    inventory_mode = fields.Selection([
        ('full', 'Full Inventory'),
        ('cycle', 'Cycle Count'),
        ('location', 'By Location'),
        ('product', 'By Product'),
        ('lot', 'By Lot/Serial'),
    ], string='Inventory Mode', default='full')
    
    cycle_count_date = fields.Date(string='Last Cycle Count')
    cycle_frequency = fields.Integer(string='Cycle Frequency (days)', default=30)
    
class InventoryResultLine(models.Model):
    _name = 'inventory.result.line'
    _description = 'Inventory Result Line'
    
    product_id = fields.Many2one('product.product', required=True)
    location_id = fields.Many2one('stock.location', required=True)
    lot_id = fields.Many2one('stock.lot')
    theoretical_qty = fields.Float(string='System Qty')
    counted_qty = fields.Float(string='Counted Qty')
    difference_qty = fields.Float(compute='_compute_difference', store=True)
    inventory_date = fields.Datetime(default=fields.Datetime.now)
    
    @api.depends('theoretical_qty', 'counted_qty')
    def _compute_difference(self):
        for line in self:
            line.difference_qty = line.counted_qty - line.theoretical_qty
    
    def action_auto_create_adjustment(self):
        """Tự động tạo phiếu điều chỉnh khi có chênh lệch kiểm kê"""
        for line in self.filtered(lambda l: l.difference_qty != 0):
            if line.difference_qty > 0:
                # Thừa → tạo phiếu nhập điều chỉnh
                self._create_adjustment_receipt(line)
            else:
                # Thiếu → tạo phiếu điều chuyển về vị trí xử lý
                self._create_adjustment_transfer(line)
    
    def _create_adjustment_receipt(self, line):
        """Tạo phiếu nhập điều chỉnh cho hàng thừa"""
        # Create stock picking for adjustment
        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'incoming'),
            ('warehouse_id.company_id', '=', line.company_id.id)
        ], limit=1)
        
        if picking_type:
            picking = self.env['stock.picking'].create({
                'picking_type_id': picking_type.id,
                'location_id': picking_type.default_location_src_id.id,
                'location_dest_id': line.location_id.id,
                'origin': f'Inventory Adjustment - {line.inventory_date}',
            })
            
            self.env['stock.move'].create({
                'name': f'Adjustment: {line.product_id.name}',
                'product_id': line.product_id.id,
                'product_uom_qty': abs(line.difference_qty),
                'product_uom': line.product_id.uom_id.id,
                'picking_id': picking.id,
                'location_id': picking_type.default_location_src_id.id,
                'location_dest_id': line.location_id.id,
            })
    
    def _create_adjustment_transfer(self, line):
        """Tạo phiếu điều chuyển cho hàng thiếu về vị trí xử lý"""
        # Find processing location
        processing_loc = self.env['stock.location'].search([
            ('name', 'ilike', 'processing'),
            ('usage', '=', 'internal')
        ], limit=1)
        
        if not processing_loc:
            processing_loc = self.env['stock.location'].search([
                ('usage', '=', 'internal')
            ], limit=1)
        
        if processing_loc:
            transfer = self.env['stock.internal.transfer'].create({
                'product_id': line.product_id.id,
                'location_src_id': line.location_id.id,
                'location_dest_id': processing_loc.id,
                'quantity': abs(line.difference_qty),
                'transfer_type': 'batch' if line.lot_id else 'barcode',
                'lot_id': line.lot_id.id if line.lot_id else False,
                'notes': f'Auto-created from inventory adjustment - Missing stock',
            })
