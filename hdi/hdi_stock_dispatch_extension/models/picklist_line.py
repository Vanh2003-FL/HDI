from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PicklistLine(models.Model):
    _name = 'picklist.line'
    _description = 'Picklist Line'
    _order = 'sequence, id'

    sequence = fields.Integer(string='Sequence', default=10)
    picklist_id = fields.Many2one(
        'picking.picklist',
        string='Picklist',
        required=True,
        ondelete='cascade'
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True
    )
    location_id = fields.Many2one(
        'stock.location',
        string='Source Location',
        required=True,
        domain=[('usage', '=', 'internal')]
    )
    lot_id = fields.Many2one(
        'stock.lot',
        string='Lot/Serial',
        domain="[('product_id', '=', product_id)]"
    )
    
    # Quantities
    qty_ordered = fields.Float(
        string='Ordered Qty',
        required=True,
        digits='Product Unit of Measure'
    )
    picked_qty = fields.Float(
        string='Picked Qty',
        digits='Product Unit of Measure',
        default=0.0
    )
    uom_id = fields.Many2one(
        'uom.uom',
        string='UoM',
        related='product_id.uom_id',
        readonly=True
    )
    
    # Status
    is_picked = fields.Boolean(
        string='Picked',
        compute='_compute_is_picked',
        store=True
    )
    
    # Package
    package_id = fields.Many2one(
        'stock.quant.package',
        string='Package'
    )
    
    notes = fields.Char(string='Notes')

    @api.depends('qty_ordered', 'picked_qty')
    def _compute_is_picked(self):
        for line in self:
            line.is_picked = line.picked_qty >= line.qty_ordered

    @api.constrains('picked_qty', 'qty_ordered')
    def _check_picked_qty(self):
        for line in self:
            if line.picked_qty < 0:
                raise ValidationError(_('Picked quantity cannot be negative.'))
            if line.picked_qty > line.qty_ordered:
                raise ValidationError(_('Picked quantity cannot exceed ordered quantity.'))

    def action_mark_picked(self):
        for line in self:
            line.picked_qty = line.qty_ordered

    def get_fifo_suggestion(self):
        """FIFO logic: Lấy hàng từ batch/lot cũ nhất trước"""
        self.ensure_one()
        
        # Find oldest lots with available quantity
        quants = self.env['stock.quant'].search([
            ('product_id', '=', self.product_id.id),
            ('location_id', '=', self.location_id.id),
            ('quantity', '>', 0),
            ('lot_id', '!=', False),
        ], order='lot_id.create_date asc')
        
        suggestions = []
        remaining_qty = self.qty_ordered
        
        for quant in quants:
            if remaining_qty <= 0:
                break
            
            take_qty = min(quant.quantity, remaining_qty)
            suggestions.append({
                'lot': quant.lot_id.name,
                'location': quant.location_id.name,
                'available_qty': quant.quantity,
                'take_qty': take_qty,
                'lot_date': quant.lot_id.create_date,
            })
            remaining_qty -= take_qty
        
        return suggestions
