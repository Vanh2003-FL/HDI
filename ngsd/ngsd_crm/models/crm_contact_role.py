from odoo import models, fields, api, _, exceptions
from odoo.exceptions import UserError, ValidationError


class CRMContactRole(models.Model):
    _name = 'crm.contact.role'
    _description = 'CRM Contact Role'

    name = fields.Char(
        required=True,
        index=True,
    )
