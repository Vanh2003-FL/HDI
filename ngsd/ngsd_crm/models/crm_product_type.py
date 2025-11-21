from odoo import api, fields, models, Command, _
from odoo.exceptions import UserError, ValidationError


class CrmProductType(models.Model):
    _name = 'crm.product.type'
    _description = 'Crm Product Type'

    name = fields.Char(
        required=True,
        index=True,
    )

    company_id = fields.Many2one('res.company', string="Công ty", default=lambda self: self.env.company)
    