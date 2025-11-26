# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class WmsDelivery(models.Model):
    _inherit = 'wms.delivery'

    # 3PL Integration
    use_3pl = fields.Boolean(string='Use 3PL Carrier', default=False)
    logistics_partner_id = fields.Many2one('logistics.partner', string='3PL Carrier')
    service_type = fields.Selection([
        ('standard', 'Standard'),
        ('express', 'Express'),
        ('same_day', 'Same Day'),
        ('next_day', 'Next Day'),
        ('economy', 'Economy'),
    ], string='Service Type', default='standard')
    
    # Tracking
    tracking_id = fields.Many2one('logistics.tracking', string='Shipment Tracking')
    carrier_tracking_ref = fields.Char(related='tracking_id.carrier_tracking_ref',
                                      string='Tracking Number', readonly=True)
    tracking_state = fields.Selection(related='tracking_id.state', string='Tracking Status',
                                     readonly=True)
    
    # Costs
    estimated_shipping_cost = fields.Monetary(string='Estimated Shipping Cost',
                                             currency_field='currency_id')
    actual_shipping_cost = fields.Monetary(related='tracking_id.shipping_cost',
                                          string='Actual Shipping Cost',
                                          currency_field='currency_id', readonly=True)
    
    # COD
    is_cod = fields.Boolean(string='COD', default=False)
    cod_amount = fields.Monetary(string='COD Amount', currency_field='currency_id')

    def action_create_shipment(self):
        """Create 3PL shipment"""
        self.ensure_one()
        
        if not self.use_3pl or not self.logistics_partner_id:
            raise UserError(_('Please configure 3PL settings first!'))
        
        # Calculate shipping cost
        weight = sum(self.line_ids.mapped(lambda l: l.product_id.weight * l.quantity_done))
        
        shipping_cost = self.logistics_partner_id.calculate_shipping_cost(
            weight=weight,
            from_province=self.warehouse_id.partner_id.state_id,
            to_province=self.partner_shipping_id.state_id,
            service_type=self.service_type
        )
        
        # Create tracking record
        tracking = self.env['logistics.tracking'].create({
            'delivery_id': self.id,
            'partner_id': self.logistics_partner_id.id,
            'service_type': self.service_type,
            'weight': weight,
            'is_cod': self.is_cod,
            'cod_amount': self.cod_amount,
            'shipping_cost': shipping_cost,
            'sla_days': self._get_sla_days(),
        })
        
        self.write({
            'tracking_id': tracking.id,
            'estimated_shipping_cost': shipping_cost,
        })
        
        # Create shipment with carrier
        tracking.action_create_shipment()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Shipment created successfully!'),
                'type': 'success',
                'sticky': False,
            }
        }

    def _get_sla_days(self):
        """Get SLA days based on service type"""
        sla_map = {
            'same_day': 1,
            'next_day': 1,
            'express': 2,
            'standard': 3,
            'economy': 5,
        }
        return sla_map.get(self.service_type, 3)

    def action_view_tracking(self):
        """View tracking details"""
        self.ensure_one()
        
        if not self.tracking_id:
            raise UserError(_('No tracking information available!'))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Shipment Tracking'),
            'res_model': 'logistics.tracking',
            'res_id': self.tracking_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
