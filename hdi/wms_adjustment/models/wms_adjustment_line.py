# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class WmsAdjustmentLine(models.Model):
    _name = 'wms.adjustment.line'
    _description = 'WMS Adjustment Line'
    _order = 'id'

    adjustment_id = fields.Many2one(
        'wms.adjustment',
        string='Adjustment',
        required=True,
        ondelete='cascade'
    )
    
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        domain=[('type', '=', 'product')]
    )
    
    lot_id = fields.Many2one(
        'stock.lot',
        string='Lot/Serial Number',
        domain="[('product_id', '=', product_id)]"
    )
    
    theoretical_qty = fields.Float(
        string='Theoretical Quantity',
        required=True,
        default=0.0,
        digits='Product Unit of Measure',
        help='Current quantity in system'
    )
    
    counted_qty = fields.Float(
        string='Counted Quantity',
        default=0.0,
        digits='Product Unit of Measure',
        help='Physically counted quantity'
    )
    
    variance_qty = fields.Float(
        string='Variance',
        compute='_compute_variance',
        store=True,
        digits='Product Unit of Measure'
    )
    
    variance_percent = fields.Float(
        string='Variance %',
        compute='_compute_variance',
        store=True
    )
    
    variance_status = fields.Selection([
        ('no_variance', 'No Variance'),
        ('acceptable', 'Acceptable'),
        ('warning', 'Warning'),
        ('critical', 'Critical')
    ], string='Status', compute='_compute_variance', store=True)
    
    product_uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        related='product_id.uom_id',
        readonly=True
    )
    
    state = fields.Selection(
        related='adjustment_id.state',
        string='Status',
        store=True
    )
    
    notes = fields.Text(
        string='Notes'
    )

    @api.depends('theoretical_qty', 'counted_qty')
    def _compute_variance(self):
        for line in self:
            line.variance_qty = line.counted_qty - line.theoretical_qty
            
            # Calculate percentage
            if line.theoretical_qty != 0:
                line.variance_percent = (line.variance_qty / line.theoretical_qty) * 100
            else:
                line.variance_percent = 100.0 if line.counted_qty > 0 else 0.0
            
            # Determine status based on variance percentage
            abs_variance = abs(line.variance_percent)
            if abs_variance == 0:
                line.variance_status = 'no_variance'
            elif abs_variance <= 5:
                line.variance_status = 'acceptable'
            elif abs_variance <= 15:
                line.variance_status = 'warning'
            else:
                line.variance_status = 'critical'

    @api.constrains('theoretical_qty', 'counted_qty')
    def _check_quantities(self):
        for line in self:
            if line.theoretical_qty < 0:
                raise ValidationError(_('Theoretical quantity cannot be negative.'))
            if line.counted_qty < 0:
                raise ValidationError(_('Counted quantity cannot be negative.'))

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Auto-load theoretical quantity from current stock"""
        if self.product_id and self.adjustment_id.location_id:
            quant_obj = self.env['wms.stock.quant']
            domain = [
                ('product_id', '=', self.product_id.id),
                ('location_id', '=', self.adjustment_id.location_id.id)
            ]
            if self.lot_id:
                domain.append(('lot_id', '=', self.lot_id.id))
            
            quants = quant_obj.search(domain)
            self.theoretical_qty = sum(quants.mapped('quantity'))
