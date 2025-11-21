from odoo import api, fields, models
import json


class CRMTeam(models.Model):
    _inherit = 'crm.team'

    user_ids = fields.Many2many('res.users', string="Trưởng nhóm")
