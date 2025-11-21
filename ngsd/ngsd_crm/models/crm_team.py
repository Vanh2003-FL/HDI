from odoo import models, fields, api, _
import json


class CRMTeam(models.Model):
    _inherit = 'crm.team'

    user_ids = fields.Many2many('res.users', string="Trưởng nhóm")
