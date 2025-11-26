from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    is_3pl_provider = fields.Boolean(string='Is 3PL Provider')
    logistics_partner_ids = fields.One2many('logistics.partner', 'partner_id')
