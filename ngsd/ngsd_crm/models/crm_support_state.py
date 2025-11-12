from odoo import api, fields, models, Command, _
from odoo.exceptions import UserError, ValidationError


class CrmSupportState(models.Model):
    _name = 'crm.support.state'
    _description = 'Crm Support State'

    name = fields.Char(
        required=True,
        index=True,
    )
