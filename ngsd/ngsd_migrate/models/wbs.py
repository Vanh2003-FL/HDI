from odoo import models, fields, api
import json
from lxml import etree


class Wbs(models.Model):
    _inherit = 'en.wbs'

    state = fields.Selection(readonly=False)
    version_number = fields.Char(readonly=False, compute=False)
    project_id = fields.Many2one(readonly=False)
    user_id = fields.Many2one(required=False)
    resource_plan_id = fields.Many2one(required=False)


class ProjectStage(models.Model):
    _inherit = 'en.project.stage'

    stage_code = fields.Char(readonly=False, compute=False)
    state = fields.Selection(readonly=False)
