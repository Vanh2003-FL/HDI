from odoo import models, fields, api
import json
from lxml import etree


class Workpackage(models.Model):
    _inherit = 'en.workpackage'

    en_real_start_date = fields.Datetime(readonly=False)
    en_real_end_date = fields.Datetime(readonly=False)
    state = fields.Selection(readonly=False)
    wp_code = fields.Char(readonly=False, compute=False)
    user_id = fields.Many2one(required=False)

    def _constrains_date(self):
        return
