from odoo import api, fields, models, Command, _
from odoo.exceptions import UserError, ValidationError
import json


class XLegal(models.Model):
    _name = 'x.legal'
    _description = "Pháp nhân"

    name = fields.Char(string="Pháp nhân", required=True)
