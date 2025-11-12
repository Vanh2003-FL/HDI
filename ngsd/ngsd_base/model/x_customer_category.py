from odoo import api, fields, models, Command, _
from odoo.exceptions import UserError, ValidationError
import json


class XCustomerCategory(models.Model):
    _name = 'x.customer.category'
    _description = "Mảng khách hàng"

    name = fields.Char(string="Mảng khách hàng", required=True)
