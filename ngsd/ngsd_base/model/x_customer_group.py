from odoo import api, fields, models, Command, _
from odoo.exceptions import UserError, ValidationError
import json


class XCustomerGroup(models.Model):
    _name = 'x.customer.group'
    _description = "Nhóm khách hàng"

    name = fields.Char(string="Nhóm khách hàng", required=True)
