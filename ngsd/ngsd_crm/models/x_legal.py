from odoo import models, fields, api, _, exceptions
from odoo.exceptions import UserError, ValidationError
import json


class XLegal(models.Model):
    _name = 'x.legal'
    _description = "Pháp nhân"

    name = fields.Char(string="Pháp nhân", required=True)
