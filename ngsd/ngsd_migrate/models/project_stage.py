from odoo import models, fields, api, _
import json
from lxml import etree


class ProjectStage(models.Model):
    _inherit = 'en.project.stage'

    en_real_start_date = fields.Datetime(readonly=False)
    en_real_end_date = fields.Datetime(readonly=False)

    def _en_constrains_en_start_date(self):
        return