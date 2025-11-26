# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class LogisticsRate(models.Model):
    _name = 'logistics.rate'
    _description = 'Logistics Rate Table'
    _order = 'partner_id, service_type, weight_from'

    name = fields.Char(string='Rate Name', compute='_compute_name', store=True)
    partner_id = fields.Many2one('logistics.partner', string='Carrier', required=True,
                                 ondelete='cascade')
    
    # Service type
    service_type = fields.Selection([
        ('standard', 'Standard Delivery'),
        ('express', 'Express Delivery'),
        ('same_day', 'Same Day Delivery'),
        ('next_day', 'Next Day Delivery'),
        ('economy', 'Economy'),
    ], string='Service Type', required=True, default='standard')
    
    # Weight range (kg)
    weight_from = fields.Float(string='Weight From (kg)', required=True, default=0.0,
                              digits=(10, 2))
    weight_to = fields.Float(string='Weight To (kg)', required=True, default=1.0,
                            digits=(10, 2))
    
    # Zone-based pricing
    from_zone_id = fields.Many2one('logistics.zone', string='From Zone',
                                   help='Leave empty for all zones')
    to_zone_id = fields.Many2one('logistics.zone', string='To Zone',
                                 help='Leave empty for all zones')
    
    # Pricing
    base_rate = fields.Monetary(string='Base Rate', required=True, currency_field='currency_id',
                                help='Base rate for first kg')
    per_kg_rate = fields.Monetary(string='Per KG Rate', currency_field='currency_id',
                                  help='Additional rate per kg after first kg')
    
    # Additional fees
    fuel_surcharge_percent = fields.Float(string='Fuel Surcharge (%)', default=0.0)
    remote_area_fee = fields.Monetary(string='Remote Area Fee', currency_field='currency_id')
    cod_fee_percent = fields.Float(string='COD Fee (%)', default=0.0,
                                   help='Fee percentage for COD service')
    
    # Validity
    valid_from = fields.Date(string='Valid From', default=fields.Date.today)
    valid_to = fields.Date(string='Valid To')
    active = fields.Boolean(string='Active', default=True)
    is_default = fields.Boolean(string='Is Default', default=False,
                               help='Use as default rate if no specific rate found')
    
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)

    @api.depends('partner_id', 'service_type', 'weight_from', 'weight_to')
    def _compute_name(self):
        for rate in self:
            rate.name = f'{rate.partner_id.name} - {rate.service_type} - {rate.weight_from}-{rate.weight_to}kg'

    @api.constrains('weight_from', 'weight_to')
    def _check_weight_range(self):
        for rate in self:
            if rate.weight_from >= rate.weight_to:
                raise ValidationError(_('Weight From must be less than Weight To!'))

    def calculate_total_cost(self, weight, is_cod=False, is_remote=False):
        """Calculate total shipping cost including surcharges"""
        self.ensure_one()
        
        # Base cost
        total = self.base_rate
        
        # Add per-kg cost
        if weight > 1:
            total += (weight - 1) * self.per_kg_rate
        
        # Add fuel surcharge
        if self.fuel_surcharge_percent > 0:
            total += total * (self.fuel_surcharge_percent / 100)
        
        # Add remote area fee
        if is_remote and self.remote_area_fee > 0:
            total += self.remote_area_fee
        
        # Add COD fee
        if is_cod and self.cod_fee_percent > 0:
            # Note: COD fee usually calculated on shipment value, not shipping cost
            # This is placeholder - actual implementation should use shipment value
            pass
        
        return total


class LogisticsZone(models.Model):
    _name = 'logistics.zone'
    _description = 'Logistics Zone for Rate Calculation'

    name = fields.Char(string='Zone Name', required=True)
    code = fields.Char(string='Zone Code', required=True)
    
    # Geographic coverage
    country_id = fields.Many2one('res.country', string='Country', required=True)
    state_id = fields.Many2one('res.country.state', string='State/Province')
    province_ids = fields.Many2many('res.country.state', string='Provinces')
    
    # Zone type
    zone_type = fields.Selection([
        ('urban', 'Urban'),
        ('suburban', 'Suburban'),
        ('rural', 'Rural'),
        ('remote', 'Remote Area'),
    ], string='Zone Type', default='urban')
    
    is_remote = fields.Boolean(string='Is Remote Area', default=False,
                               help='Apply remote area surcharge')
    active = fields.Boolean(string='Active', default=True)
