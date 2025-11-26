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
