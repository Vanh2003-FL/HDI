# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class WmsDeliveryLine(models.Model):
    _name = 'wms.delivery.line'
    _description = 'WMS Delivery Line'
    _order = 'delivery_id, sequence, id'

    sequence = fields.Integer(string='Sequence', default=10)
    delivery_id = fields.Many2one('wms.delivery', string='Delivery', required=True,
                                  ondelete='cascade', index=True)
    state = fields.Selection(related='delivery_id.state', string='Delivery State', store=True)
    
    # Product
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='restrict')
    product_uom_id = fields.Many2one('uom.uom', string='UoM', related='product_id.uom_id', store=True)
    
    # Quantities
    ordered_qty = fields.Float(string='Ordered Qty', digits='Product Unit of Measure', required=True, default=1.0)
    picked_qty = fields.Float(string='Picked Qty', digits='Product Unit of Measure', default=0.0)
    delivered_qty = fields.Float(string='Delivered Qty', digits='Product Unit of Measure', default=0.0)
    
    # Availability
    availability_status = fields.Selection([
        ('unavailable', 'Unavailable'),
        ('partial', 'Partially Available'),
        ('available', 'Available'),
    ], string='Availability', default='unavailable')
    
    # Picking lines
    picking_line_ids = fields.One2many('wms.delivery.picking.line', 'delivery_line_id', string='Picking Lines')
    
    note = fields.Text(string='Notes')

    @api.constrains('ordered_qty', 'picked_qty')
    def _check_quantities(self):
        for record in self:
            if record.ordered_qty < 0:
                raise ValidationError(_('Ordered quantity cannot be negative!'))
            if record.picked_qty < 0:
                raise ValidationError(_('Picked quantity cannot be negative!'))


class WmsDeliveryPickingLine(models.Model):
    _name = 'wms.delivery.picking.line'
    _description = 'WMS Delivery Picking Line'
    _order = 'delivery_line_id, sequence'

    sequence = fields.Integer(string='Sequence', default=10)
    delivery_line_id = fields.Many2one('wms.delivery.line', string='Delivery Line', required=True, ondelete='cascade')
    product_id = fields.Many2one(related='delivery_line_id.product_id', string='Product', store=True)
    
    location_id = fields.Many2one('wms.location', string='Pick From Location', required=True)
    lot_id = fields.Many2one('stock.lot', string='Lot/Serial')
    
    quantity = fields.Float(string='Quantity to Pick', digits='Product Unit of Measure', required=True)
    picked_quantity = fields.Float(string='Picked Qty', digits='Product Unit of Measure', default=0.0)
    
    status = fields.Selection([
        ('assigned', 'Assigned'),
        ('picking', 'Picking'),
        ('picked', 'Picked'),
    ], string='Status', default='assigned')
