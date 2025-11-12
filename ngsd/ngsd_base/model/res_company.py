from odoo import models, fields, api


class ResCompany(models.Model):
    _inherit = 'res.company'

    company_type = fields.Char(string='Loại Công ty', default='ngsd', required=1)
