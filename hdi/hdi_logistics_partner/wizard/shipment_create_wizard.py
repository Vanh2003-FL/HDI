# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ShipmentCreateWizard(models.TransientModel):
    _name = 'shipment.create.wizard'
    _description = 'Create 3PL Shipment Wizard'

    delivery_id = fields.Many2one('wms.delivery', string='Delivery Order', required=True)
    
    # Carrier selection
    logistics_partner_id = fields.Many2one('logistics.partner', string='Carrier', required=True,
                                          domain=[('state', '=', 'active')])
    service_type = fields.Selection([
        ('standard', 'Standard Delivery'),
        ('express', 'Express Delivery'),
        ('same_day', 'Same Day Delivery'),
        ('next_day', 'Next Day Delivery'),
        ('economy', 'Economy'),
    ], string='Service Type', default='standard', required=True)
    
    # Package details
    weight = fields.Float(string='Weight (kg)', required=True, digits=(10, 2))
    length = fields.Float(string='Length (cm)', digits=(10, 2))
    width = fields.Float(string='Width (cm)', digits=(10, 2))
    height = fields.Float(string='Height (cm)', digits=(10, 2))
    
    # COD
    is_cod = fields.Boolean(string='COD Shipment', default=False)
    cod_amount = fields.Monetary(string='COD Amount', currency_field='currency_id')
    
    # Cost calculation
    estimated_cost = fields.Monetary(string='Estimated Cost', compute='_compute_estimated_cost',
                                    currency_field='currency_id')
    
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)
    
    # Notes
    notes = fields.Text(string='Special Instructions')

    @api.depends('logistics_partner_id', 'weight', 'service_type', 'delivery_id')
    def _compute_estimated_cost(self):
        for wizard in self:
            if wizard.logistics_partner_id and wizard.weight and wizard.delivery_id:
                cost = wizard.logistics_partner_id.calculate_shipping_cost(
                    weight=wizard.weight,
                    from_province=wizard.delivery_id.warehouse_id.partner_id.state_id,
                    to_province=wizard.delivery_id.partner_shipping_id.state_id,
                    service_type=wizard.service_type
                )
                wizard.estimated_cost = cost
            else:
                wizard.estimated_cost = 0.0

    @api.onchange('delivery_id')
    def _onchange_delivery_id(self):
        """Auto-fill weight from delivery lines"""
        if self.delivery_id:
            total_weight = sum(self.delivery_id.line_ids.mapped(
                lambda l: l.product_id.weight * l.quantity_done
            ))
            self.weight = total_weight or 1.0

    def action_create_shipment(self):
        """Create shipment"""
        self.ensure_one()
        
        # Create tracking record
        tracking = self.env['logistics.tracking'].create({
            'delivery_id': self.delivery_id.id,
            'partner_id': self.logistics_partner_id.id,
            'service_type': self.service_type,
            'weight': self.weight,
            'length': self.length,
            'width': self.width,
            'height': self.height,
            'is_cod': self.is_cod,
            'cod_amount': self.cod_amount,
            'shipping_cost': self.estimated_cost,
        })
        
        # Update delivery
        self.delivery_id.write({
            'use_3pl': True,
            'logistics_partner_id': self.logistics_partner_id.id,
            'service_type': self.service_type,
            'tracking_id': tracking.id,
            'is_cod': self.is_cod,
            'cod_amount': self.cod_amount,
        })
        
        # Create shipment with carrier API
        tracking.action_create_shipment()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Shipment Tracking'),
            'res_model': 'logistics.tracking',
            'res_id': tracking.id,
            'view_mode': 'form',
            'target': 'current',
        }
