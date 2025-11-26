from odoo import models, fields

class LogisticsRate(models.Model):
    _name = 'logistics.rate'
    _description = 'Logistics Rate'
    
    partner_id = fields.Many2one('logistics.partner', required=True)
    min_weight = fields.Float()
    max_weight = fields.Float()
    rate_per_kg = fields.Float()
    fixed_rate = fields.Float()
    zone = fields.Char()
    
