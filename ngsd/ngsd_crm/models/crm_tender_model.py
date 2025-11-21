from odoo import models, fields, api, _, exceptions
from odoo.exceptions import UserError, ValidationError


class CrmTenderModel(models.Model):
    _name = 'crm.tender.model'
    _description = 'Crm Tender Model'

    name = fields.Char(
        required=True,
        index=True,
    )
