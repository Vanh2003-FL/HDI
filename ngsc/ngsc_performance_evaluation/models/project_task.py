from odoo import fields, models, api
from odoo.exceptions import ValidationError, UserError, AccessError


class ProjectTask(models.Model):
    _inherit = "project.task"

    project_task_evaluation_ids = fields.One2many("task.evaluation", "project_task_id",
                                                  string="Danh sách đánh giá công việc theo tháng")
    date_evaluation = fields.Boolean(string="Thời gian đánh giá", search="_search_check_evaluation", store=False)

    @api.model
    def _search_check_evaluation(self, operator, value):
        project_tasks = self.env["project.task"].search([])
        task_evaluations = self.env["task.evaluation"].search([
            ("project_task_id", "in", project_tasks.ids),
            ("date_evaluation", "=", value),
            ("state", "=", "not_evaluated")])
        records = task_evaluations.mapped("project_task_id.id")
        return [("id", "in", records)]