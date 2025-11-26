from odoo import models, fields, api

class LogisticsPartner(models.Model):
    _name = 'logistics.partner'
    _description = 'Logistics Partner (3PL)'
    
    name = fields.Char(required=True)
    partner_id = fields.Many2one('res.partner', required=True)
    api_endpoint = fields.Char(string='API Endpoint')
    api_key = fields.Char(string='API Key')
    service_type = fields.Selection([
        ('express', 'Express'),
        ('standard', 'Standard'),
        ('economy', 'Economy'),
    ])
    coverage_area_ids = fields.Many2many('res.country.state', string='Coverage Areas')
    active = fields.Boolean(default=True)
    
