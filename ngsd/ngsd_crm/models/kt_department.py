from odoo import api, fields, models, Command, _
from odoo.exceptions import UserError, ValidationError
import json


class KTDepartment(models.Model):
    _name = 'kt.department'
    _description = "Phòng kỹ thuật"

    name = fields.Char(string="Pháp nhân", required=True)
