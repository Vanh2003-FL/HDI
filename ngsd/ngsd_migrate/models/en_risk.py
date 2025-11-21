from odoo import models, fields, api
import json
from lxml import etree


class ENRisk(models.Model):
    _inherit = 'en.risk'

    project_id = fields.Many2one(readonly=False)
    date_end = fields.Date(readonly=False)


class ENProblem(models.Model):
    _inherit = 'en.problem'

    project_id = fields.Many2one(readonly=False)

    def _constrains_deadline(self):
        return

    def _constrains_deadline(self):
        return


class RiskType(models.Model):
    _inherit = 'en.risk.type'

    def _constrains_code(self):
        return
