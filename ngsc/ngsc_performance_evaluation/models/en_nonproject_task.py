from odoo import fields, models, api
from odoo.exceptions import ValidationError, UserError, AccessError
from ..utils.constant import *
from dateutil.relativedelta import relativedelta


class NonProjectTask(models.Model):
    _inherit = "en.nonproject.task"

    effective_hours = fields.Float(string="Số giờ thực tế", compute="_compute_effective_hours", store=True)
    nonproject_task_evaluation_ids = fields.One2many("task.evaluation", "nonproject_task_id",
                                                     string="Danh sách đánh giá công việc theo tháng")
    date_evaluation = fields.Boolean(string="Thời gian đánh giá", search="_search_check_evaluation", store=False)

    @api.model
    def _search_check_evaluation(self, operator, value):
        nonproject_tasks = self.env["en.nonproject.task"].search([])
        task_evaluations = self.env["task.evaluation"].search([
            ("nonproject_task_id", "in", nonproject_tasks.ids),
            ("date_evaluation", "=", value),
            ("state", "=", "not_evaluated")])
        records = task_evaluations.mapped("nonproject_task_id.id")
        return [("id", "in", records)]

    @api.depends('timesheet_ids.ot_time', 'timesheet_ids.en_state', 'timesheet_ids.ot_state',
                 'timesheet_ids.unit_amount')
    def _compute_effective_hours(self):
        for rec in self:
            effective_hours = 0
            effective_hours += sum(
                rec.timesheet_ids.filtered(lambda x: x.en_state in ['approved', 'waiting']).mapped('unit_amount'))
            effective_hours += sum(rec.timesheet_ids.filtered(lambda x: x.ot_state == 'approved').mapped('ot_time'))
            rec.effective_hours = effective_hours