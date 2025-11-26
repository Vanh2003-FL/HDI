# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class WmsReceiptLine(models.Model):
    _name = 'wms.receipt.line'
    _description = 'WMS Receipt Line'
    _order = 'receipt_id, sequence, id'

    sequence = fields.Integer(string='Sequence', default=10)
    receipt_id = fields.Many2one('wms.receipt', string='Receipt', required=True,
                                 ondelete='cascade', index=True)
    state = fields.Selection(related='receipt_id.state', string='Receipt State', store=True)
    
    # Product
    product_id = fields.Many2one('product.product', string='Product', required=True,
                                 ondelete='restrict')
    product_uom_id = fields.Many2one('uom.uom', string='UoM',
                                     related='product_id.uom_id', store=True)
    
    # Lot/Serial
    lot_id = fields.Many2one('stock.lot', string='Lot/Serial Number')
    expiration_date = fields.Date(string='Expiration Date')
    
    # Quantities
    expected_qty = fields.Float(string='Expected Qty', digits='Product Unit of Measure',
                               required=True, default=1.0)
    received_qty = fields.Float(string='Received Qty', digits='Product Unit of Measure',
                               default=0.0)
    difference_qty = fields.Float(string='Difference', compute='_compute_difference_qty',
                                 store=True, digits='Product Unit of Measure')
    
    # Putaway
    putaway_location_id = fields.Many2one('wms.location', string='Putaway Location',
                                         domain="[('zone_id.zone_type', '=', 'storage')]")
    
    # Quality Check
    quality_status = fields.Selection([
        ('pending', 'Pending'),
        ('passed', 'Passed'),
        ('failed', 'Failed'),
    ], string='Quality Status', default='pending')
    quality_notes = fields.Text(string='QC Notes')
    
    # Damage
    damaged_qty = fields.Float(string='Damaged Qty', digits='Product Unit of Measure',
                              default=0.0)
    damage_notes = fields.Text(string='Damage Notes')
    
    # Additional Info
    note = fields.Text(string='Notes')

    @api.depends('expected_qty', 'received_qty')
    def _compute_difference_qty(self):
        for record in self:
            record.difference_qty = record.received_qty - record.expected_qty

    @api.constrains('expected_qty', 'received_qty', 'damaged_qty')
    def _check_quantities(self):
        for record in self:
            if record.expected_qty < 0:
                raise ValidationError(_('Expected quantity cannot be negative!'))
            if record.received_qty < 0:
                raise ValidationError(_('Received quantity cannot be negative!'))
            if record.damaged_qty < 0:
                raise ValidationError(_('Damaged quantity cannot be negative!'))
            if record.damaged_qty > record.received_qty:
                raise ValidationError(_('Damaged quantity cannot exceed received quantity!'))

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Set expiration date based on product shelf life"""
        if self.product_id and self.product_id.wms_shelf_life_days:
            from datetime import timedelta
            self.expiration_date = fields.Date.today() + timedelta(days=self.product_id.wms_shelf_life_days)

    def action_set_quality_pass(self):
        """Pass quality for this line"""
        self.write({'quality_status': 'passed'})
        self.receipt_id.message_post(body=_('Quality passed for: %s') % self.product_id.display_name)

    def action_set_quality_fail(self):
        """Fail quality for this line"""
        self.write({'quality_status': 'failed'})
        self.receipt_id.message_post(body=_('Quality failed for: %s') % self.product_id.display_name)
