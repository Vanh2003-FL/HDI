# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import timedelta


class CycleCountWizard(models.TransientModel):
    _name = 'cycle.count.wizard'
    _description = 'Cycle Count Wizard'

    warehouse_id = fields.Many2one(
        'wms.warehouse',
        string='Warehouse',
        required=True,
        default=lambda self: self.env['wms.warehouse'].search([], limit=1)
    )
    
    location_ids = fields.Many2many(
        'wms.location',
        string='Locations',
        domain="[('warehouse_id', '=', warehouse_id)]",
        help='Leave empty to count all locations'
    )
    
    product_ids = fields.Many2many(
        'product.product',
        string='Products',
        domain=[('type', '=', 'product')],
        help='Leave empty to count all products'
    )
    
    count_zero_stock = fields.Boolean(
        string='Include Zero Stock Products',
        default=False,
        help='Include products with zero stock in counting'
    )
    
    abc_classification = fields.Selection([
        ('a', 'Class A (High Value)'),
        ('b', 'Class B (Medium Value)'),
        ('c', 'Class C (Low Value)')
    ], string='ABC Classification', help='Count only products of specific ABC class')
    
    last_counted_days = fields.Integer(
        string='Last Counted (Days Ago)',
        help='Count products not counted in X days. Leave 0 to ignore.'
    )
    
    reason_id = fields.Many2one(
        'wms.adjustment.reason',
        string='Reason',
        required=True,
        domain="[('adjustment_type', '=', 'cycle_count')]",
        default=lambda self: self.env.ref('wms_adjustment.reason_cycle_count', raise_if_not_found=False)
    )

    def action_create_cycle_count(self):
        """Create cycle count adjustment(s)"""
        self.ensure_one()
        
        # Determine locations
        locations = self.location_ids or self.env['wms.location'].search([
            ('warehouse_id', '=', self.warehouse_id.id),
            ('location_type_id.name', '=', 'Bin')  # Only count bin locations
        ])
        
        if not locations:
            raise UserError(_('No locations found for cycle counting.'))
        
        # Build product domain
        product_domain = [('type', '=', 'product')]
        if self.product_ids:
            product_domain.append(('id', 'in', self.product_ids.ids))
        if self.abc_classification:
            product_domain.append(('abc_classification', '=', self.abc_classification))
        
        # Create one adjustment per location
        adjustments = self.env['wms.adjustment']
        for location in locations:
            # Get stock in this location
            quant_domain = [
                ('location_id', '=', location.id),
                ('product_id', 'in', self.env['product.product'].search(product_domain).ids)
            ]
            
            if not self.count_zero_stock:
                quant_domain.append(('quantity', '>', 0))
            
            # Filter by last counted date if specified
            if self.last_counted_days > 0:
                cutoff_date = fields.Datetime.now() - timedelta(days=self.last_counted_days)
                # This would need a last_counted_date field on quant (future enhancement)
                # quant_domain.append(('last_counted_date', '<', cutoff_date))
            
            quants = self.env['wms.stock.quant'].search(quant_domain)
            
            if not quants:
                continue
            
            # Create adjustment
            adjustment_vals = {
                'warehouse_id': self.warehouse_id.id,
                'location_id': location.id,
                'adjustment_type': 'cycle_count',
                'reason_id': self.reason_id.id,
            }
            adjustment = adjustments.create(adjustment_vals)
            
            # Create lines from quants
            for quant in quants:
                line_vals = {
                    'adjustment_id': adjustment.id,
                    'product_id': quant.product_id.id,
                    'lot_id': quant.lot_id.id if quant.lot_id else False,
                    'theoretical_qty': quant.quantity,
                    'counted_qty': 0.0,  # To be filled during counting
                }
                self.env['wms.adjustment.line'].create(line_vals)
        
        if not adjustments:
            raise UserError(_('No stock found matching the criteria.'))
        
        # Return action to view created adjustments
        action = self.env.ref('wms_adjustment.action_wms_adjustment').read()[0]
        action['domain'] = [('id', 'in', adjustments.ids)]
        action['context'] = {}
        return action
