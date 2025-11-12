from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ProjectTask(models.Model):
    _inherit = "project.task"

    bmm_stage_id = fields.Many2one("en.stage.type", string="Giai đoạn Plan", tracking=True)


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    @api.constrains("en_state", "unit_amount", "ot_time")
    def _constrains_update_resource_expense(self):
        for rec in self:
            if rec.task_id.category == "task":
                rec.project_id._update_resource_expense()