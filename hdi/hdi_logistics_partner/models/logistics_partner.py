# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import json
import logging

_logger = logging.getLogger(__name__)


class LogisticsPartner(models.Model):
    _name = 'logistics.partner'
    _description = '3PL Logistics Partner'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'

    name = fields.Char(string='Partner Name', required=True, tracking=True)
    code = fields.Char(string='Partner Code', required=True, copy=False, index=True)
    sequence = fields.Integer(string='Sequence', default=10)
    
    # Partner Type
    partner_type = fields.Selection([
        ('viettel_post', 'Viettel Post'),
        ('ghn', 'Giao Hàng Nhanh (GHN)'),
        ('jnt', 'J&T Express'),
        ('ninja_van', 'Ninja Van'),
        ('vietnam_post', 'Vietnam Post (EMS)'),
        ('best_express', 'Best Express'),
        ('custom', 'Custom API'),
    ], string='Carrier Type', required=True, tracking=True)
    
    # API Configuration
    api_url = fields.Char(string='API URL', required=True)
    api_key = fields.Char(string='API Key', required=True)
    api_secret = fields.Char(string='API Secret')
    api_token = fields.Char(string='API Token')
    shop_id = fields.Char(string='Shop ID', help='Required for GHN')
    client_code = fields.Char(string='Client Code', help='Partner account code')
    
    # Status
    active = fields.Boolean(string='Active', default=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('test', 'Testing'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
    ], string='Status', default='draft', tracking=True)
    
    # Features
    support_cod = fields.Boolean(string='Support COD', default=True,
                                 help='Cash on Delivery support')
    support_tracking = fields.Boolean(string='Support Tracking', default=True)
    support_label_print = fields.Boolean(string='Support Label Printing', default=True)
    support_bulk_create = fields.Boolean(string='Support Bulk Creation', default=False)
    
    # Service levels
    service_ids = fields.One2many('logistics.service', 'partner_id', string='Services')
    
    # Rates
    rate_ids = fields.One2many('logistics.rate', 'partner_id', string='Rate Tables')
    
    # Statistics
    shipment_count = fields.Integer(string='Total Shipments', compute='_compute_statistics')
    total_revenue = fields.Monetary(string='Total Revenue', compute='_compute_statistics',
                                    currency_field='currency_id')
    average_delivery_time = fields.Float(string='Avg Delivery Time (days)',
                                         compute='_compute_statistics')
    on_time_rate = fields.Float(string='On-Time Rate (%)', compute='_compute_statistics')
    
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)
    
    # Contact
    contact_person = fields.Char(string='Contact Person')
    contact_phone = fields.Char(string='Contact Phone')
    contact_email = fields.Char(string='Contact Email')
    
    @api.depends('name', 'code')
    def name_get(self):
        result = []
        for partner in self:
            name = f'[{partner.code}] {partner.name}'
            result.append((partner.id, name))
        return result

    def _compute_statistics(self):
        for partner in self:
            trackings = self.env['logistics.tracking'].search([
                ('partner_id', '=', partner.id)
            ])
            
            partner.shipment_count = len(trackings)
            partner.total_revenue = sum(trackings.mapped('shipping_cost'))
            
            # Calculate average delivery time
            delivered = trackings.filtered(lambda t: t.delivered_date and t.shipped_date)
            if delivered:
                total_days = sum([(t.delivered_date - t.shipped_date).days for t in delivered])
                partner.average_delivery_time = total_days / len(delivered)
            else:
                partner.average_delivery_time = 0
            
            # On-time rate
            if trackings:
                on_time = trackings.filtered(lambda t: t.is_on_time)
                partner.on_time_rate = (len(on_time) / len(trackings)) * 100
            else:
                partner.on_time_rate = 0

    def action_test_connection(self):
        """Test API connection"""
        self.ensure_one()
        
        try:
            if self.partner_type == 'viettel_post':
                result = self._test_viettel_post()
            elif self.partner_type == 'ghn':
                result = self._test_ghn()
            elif self.partner_type == 'jnt':
                result = self._test_jnt()
            elif self.partner_type == 'ninja_van':
                result = self._test_ninja_van()
            else:
                raise UserError(_('API test not implemented for this carrier type'))
            
            if result:
                self.write({'state': 'test'})
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('API connection successful!'),
                        'type': 'success',
                        'sticky': False,
                    }
                }
            
        except Exception as e:
            _logger.error(f'API test failed for {self.name}: {str(e)}')
            raise UserError(_('API connection failed: %s') % str(e))

    def _test_viettel_post(self):
        """Test Viettel Post API"""
        headers = {
            'Content-Type': 'application/json',
            'Token': self.api_token,
        }
        
        # Test endpoint - get list of services
        response = requests.get(
            f'{self.api_url}/service/getListService',
            headers=headers,
            timeout=10
        )
        
        return response.status_code == 200

    def _test_ghn(self):
        """Test GHN API"""
        headers = {
            'Content-Type': 'application/json',
            'Token': self.api_token,
            'ShopId': self.shop_id,
        }
        
        # Test endpoint - get shop info
        response = requests.post(
            f'{self.api_url}/v2/shop/all',
            headers=headers,
            timeout=10
        )
        
        return response.status_code == 200

    def _test_jnt(self):
        """Test J&T Express API"""
        headers = {
            'Content-Type': 'application/json',
            'api-key': self.api_key,
        }
        
        # Test endpoint
        response = requests.post(
            f'{self.api_url}/v1/test',
            headers=headers,
            json={'customerCode': self.client_code},
            timeout=10
        )
        
        return response.status_code == 200

    def _test_ninja_van(self):
        """Test Ninja Van API"""
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_token}',
        }
        
        # Test endpoint - get tracking info
        response = requests.get(
            f'{self.api_url}/v2/health',
            headers=headers,
            timeout=10
        )
        
        return response.status_code == 200

    def action_activate(self):
        """Activate partner"""
        self.ensure_one()
        if self.state != 'test':
            raise UserError(_('Please test the API connection first!'))
        
        self.write({'state': 'active'})

    def action_suspend(self):
        """Suspend partner"""
        self.write({'state': 'suspended'})

    def action_view_shipments(self):
        """View shipments for this partner"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Shipments - %s') % self.name,
            'res_model': 'logistics.tracking',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }

    def calculate_shipping_cost(self, weight, from_province, to_province, service_type='standard'):
        """Calculate shipping cost based on weight and zones"""
        self.ensure_one()
        
        # Find applicable rate
        rate = self.env['logistics.rate'].search([
            ('partner_id', '=', self.id),
            ('service_type', '=', service_type),
            ('weight_from', '<=', weight),
            ('weight_to', '>=', weight),
            '|',
            ('from_zone_id.province_id', '=', from_province.id),
            ('from_zone_id', '=', False),
            '|',
            ('to_zone_id.province_id', '=', to_province.id),
            ('to_zone_id', '=', False),
        ], limit=1)
        
        if not rate:
            # Use default rate if no specific rate found
            rate = self.env['logistics.rate'].search([
                ('partner_id', '=', self.id),
                ('service_type', '=', service_type),
                ('is_default', '=', True),
            ], limit=1)
        
        if rate:
            base_cost = rate.base_rate
            
            # Add per-kg cost for weight over first kg
            if weight > 1:
                base_cost += (weight - 1) * rate.per_kg_rate
            
            return base_cost
        
        return 0.0


class LogisticsService(models.Model):
    _name = 'logistics.service'
    _description = 'Logistics Service Level'
    _order = 'sequence'

    name = fields.Char(string='Service Name', required=True)
    code = fields.Char(string='Service Code', required=True)
    partner_id = fields.Many2one('logistics.partner', string='Partner', required=True,
                                 ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    
    service_type = fields.Selection([
        ('standard', 'Standard Delivery'),
        ('express', 'Express Delivery'),
        ('same_day', 'Same Day Delivery'),
        ('next_day', 'Next Day Delivery'),
        ('economy', 'Economy (Slow but Cheap)'),
    ], string='Service Type', required=True)
    
    estimated_days = fields.Integer(string='Estimated Days', default=3)
    active = fields.Boolean(string='Active', default=True)
