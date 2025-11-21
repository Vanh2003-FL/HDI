from odoo import models, fields, api, _
import json
from lxml import etree


class ProjectProject(models.Model):
    _inherit = 'project.project'

    en_real_start_date = fields.Datetime(readonly=False)
    en_real_end_date = fields.Datetime(readonly=False)
    en_bmm = fields.Float(readonly=False)

    def _constrains_en_bmm(self):
        return


class ProjectDocument(models.Model):
    _inherit = 'en.project.document'

    @api.model
    def create(self, vals):
        detail = super(ProjectDocument, self).create(vals)
        return detail
