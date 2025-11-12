from odoo import api, fields, models
import odoo.http

class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    approved_timesheet_date = fields.Date(string="Thời gian phê duyệt timesheets", index=True)
    approved_overtime_date = fields.Date(string="Thời gian phê duyệt overtime",
                                         related="ot_id.approved_overtime_date", index=True)
    en_phase_id = fields.Many2one('project.task', string='Giai đoạn dự án', compute='_get_en_phase_id', store=True,
                                  readonly=False)

    def en_button_approved(self):
        super().en_button_approved()
        today = fields.Date.Date.context_today(self)
        for rec in self:
            if rec.en_state == "approved":
                rec.sudo().write({'approved_timesheet_date': today})

    @api.depends('task_id')
    def _get_en_phase_id(self):
        for rec in self:
            phase_task = rec.task_id
            while phase_task and phase_task.category != 'phase':
                phase_task = phase_task.parent_id
            rec.en_phase_id = phase_task

    @api.model_create_multi
    def create(self, vals_list):
        ctx = self.env.context
        if (
                not odoo.http.request
                or ctx.get("skip_timesheet_notify")
                or ctx.get("from_hr_leave")
                or ctx.get("from_import")
                or ctx.get("mail_auto_delete")
                or self.env.su
        ):
            return super().create(vals_list)
        records = super().create(vals_list)
        for rec in records:
            task = rec.task_id
            if not task:
                continue

            # Lấy giá trị % hoàn thành thực tế
            fin_value = 0.0
            if hasattr(task, "en_progress"):
                fin_value = float(task.en_progress or 0)

            if fin_value >= 99.9 or fin_value >= 1.0:
                continue

            rec.env.user.notify_warning(
                message="Bạn nên cập nhật lại % Hoàn thành công việc sau khi khai Timesheet để quản lý tiện theo dõi tiến độ",
                title="Nhắc nhở",
                sticky=False,
            )
        return records