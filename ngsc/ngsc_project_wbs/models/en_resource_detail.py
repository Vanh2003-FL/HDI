from odoo import fields, models, api
from odoo.exceptions import ValidationError, UserError, AccessError


class ResourceDetail(models.Model):
    _inherit = "en.resource.detail"

    wbs_id = fields.Many2one("en.wbs", string="WBS", related="order_id.wbs_link_resource_planning", store=True)
    project_task_stage_id = fields.Many2one("project.task", string="Giai đoạn")

    @api.depends("project_task_stage_id")
    def _compute_project_stage_code(self):
        super()._compute_project_stage_code()
        for rec in self:
            rec.project_stage_code = rec.project_task_stage_id.code


    @api.constrains("project_task_stage_id", "date_start", "date_end")
    def _check_date_start_and_end(self):
        for rec in self:
            if self._context.get('no_constrains', False): continue
            if not rec.project_task_stage_id or not rec.date_start or not rec.date_end:continue
            overlaps = self.search([
                ('id', '!=', rec.id),
                ('order_id', '=', rec.order_id.id),
                ('date_start', '<=', rec.date_end),
                ('date_end', '>=', rec.date_start),
                ('employee_id', '=', rec.employee_id.id),
            ])
            overlaps = overlaps.filtered(lambda s: s.project_task_stage_id == rec.project_task_stage_id)
            if overlaps:
                raise ValidationError(
                    f'Nhân sự {rec.employee_id.name} đang bị trùng thời gian trong cùng 1 giai đoạn. Vui lòng kiểm tra lại.'
                )
            stage = rec.project_task_stage_id
            if not stage.en_start_date or not stage.date_deadline:
                continue
            if rec.date_start < stage.en_start_date or rec.date_end > stage.date_deadline:
                raise ValidationError(f'Ngày bắt đầu – kết thúc của nhân sự {rec.employee_id.name} phải nằm trong thời gian của  giai đoạn tương ứng')
