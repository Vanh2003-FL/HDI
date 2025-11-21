from odoo import api, fields, models, Command, _
from odoo.exceptions import UserError, ValidationError


class CompeteLead(models.Model):
    _name = 'compete.lead'
    _description = 'Tính cạnh tranh'

    name = fields.Char(required=True, string="Tên")
    rate = fields.Char(required=True, string="Số sao")
