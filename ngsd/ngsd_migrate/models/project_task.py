from odoo import models, fields, api, _
import json
from lxml import etree


class ProjectTask(models.Model):
    _inherit = 'project.task'

    en_open_date = fields.Datetime(readonly=False, compute=False)
    en_close_date = fields.Datetime(readonly=False, compute=False)
    en_requester = fields.Many2one(required=False)

    def _en_constrains_start_deadline_date(self):
        return

    def _en_constrains_planned_hours(self):
        return

    def _compute_en_open_date(self):
        return

    def _compute_en_open_date(self):
        return

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('project_id') and vals.get('en_task_position'):
                vals['project_id'] = self.env['en.workpackage'].browse(vals.get('en_task_position')).project_id.id
        res = super().create(vals_list)
        return res

    def _compute_en_task_code(self):
        for rec in self:
            rec.en_task_code = rec.en_task_code


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    def _en_constrains_unit_amount(self):
        return
