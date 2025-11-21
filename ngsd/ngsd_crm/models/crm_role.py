from odoo import models, fields, api, _, exceptions
from odoo.exceptions import UserError, ValidationError


class CrmRole(models.Model):
    _name = 'crm.role'
    _description = 'Crm Role'

    name = fields.Char(
        required=True,
        index=True,
    )
