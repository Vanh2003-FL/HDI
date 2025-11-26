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
