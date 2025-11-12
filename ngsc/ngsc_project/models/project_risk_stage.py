from odoo import models, fields, api

class RiskStage(models.Model):
    _inherit = 'en.risk.stage'

    active = fields.Boolean(string="Họat động", default=True)