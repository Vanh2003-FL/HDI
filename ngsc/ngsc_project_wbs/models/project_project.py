from odoo import models, fields, api, _, exceptions
from odoo.exceptions import ValidationError, UserError, AccessError


class ProjectProject(models.Model):
    _inherit = "project.project"

    def _compute_task_count(self):
        for rec in self:
            self.env.cr.execute("""
                SELECT COUNT(*)
                FROM project_task
                WHERE project_id = %s
                AND category = 'task'
                AND project_wbs_state = 'approved'
            """, (rec.id,))
            # task_ids = rec.task_ids.filtered(lambda x: x.category == "task" and x.project_wbs_state == "approved")
            result = self.env.cr.fetchone()
            rec.task_count = result[0] if result else 0
            rec.task_count_with_subtasks = 0

    def button_en_finish(self):
        for rec in self:
            if rec.en_state != 'doing':
                continue
            _domain_wbs = [('project_id', '=', rec.id),
                           ('project_wbs_state', '=', 'approved'),
                           ('category', '!=', False),
                           ('stage_id.en_mark', 'not in', ['g', 'b'])]
            if self.env['project.task'].sudo().search_count(_domain_wbs) > 0:
                raise ValidationError(
                    "Bạn cần hoàn thành tất cả các công việc, gói việc, giai đoạn trước khi hoàn thành dự án.")
            if not rec.en_real_end_date:
                rec.en_real_end_date = fields.Datetime.now()
            rec.stage_id = self.env['project.project.stage'].search([('en_state', '=', 'finish')], limit=1)
            project_code = rec.en_code
            self.env['project.quality.monthly.report'].generate_monthly_report(project_code=project_code)
            self.env['project.completion.quality.report'].generate_final_project_report(project_code=project_code)
