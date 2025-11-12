from odoo import models, api, fields
from odoo.exceptions import ValidationError


class NonProjectTask(models.Model):
    _inherit = "en.nonproject.task"

    en_estimate_hour = fields.Float(store=True, readonly=False)
    en_start_date = fields.Date(string="Ngày bắt đầu", required=True)
    en_end_date = fields.Date(string="Hạn hoàn thành", required=True)
    en_state = fields.Selection(copy=False)


    def _compute_en_estimate_hour(self):
        for rec in self:
            en_estimate_hour = 0
            if rec.en_start_date and rec.en_end_date and rec.en_pic_id.employee_id:
                # Không cần xử lý múi giờ vì trường là Date
                start_date = rec.en_start_date
                end_date = rec.en_end_date
                tech_data = self.env['en.technical.model'].convert_daterange_to_data(
                    employee=rec.en_pic_id.employee_id,
                    start_date=start_date,
                    end_date=end_date
                )
                en_estimate_hour = sum([tech_data[d].get('number') for d in tech_data])
            rec.en_estimate_hour = en_estimate_hour

    @api.model
    def create(self, vals_list):
        if 'en_start_date' not in vals_list or not vals_list.get('en_start_date'):
            raise ValidationError("Ngày bắt đầu là trường bắt buộc và không được để trống!")
        if 'en_end_date' not in vals_list or not vals_list.get('en_end_date'):
            raise ValidationError("Ngày kết thúc là trường bắt buộc và không được để trống!")

        rs = super(NonProjectTask, self).create(vals_list)
        if rs.en_supervisor_id not in rs.en_supervisor_ids:
            raise ValidationError("Người giám sát không thuộc phòng ban của công việc")
        user = rs.en_pic_id
        department = rs.en_department_id
        if user.employee_ids:
            # Lấy danh sách phòng ban của nhân viên liên quan đến user
            employee_depts = user.employee_ids.mapped('department_id')
            if department not in employee_depts:
                raise ValidationError(
                    f"Người chịu trách nhiệm {user.name} không thuộc phòng ban {department.name}."
                )
        return rs

    def write(self, values):
        res = super().write(values)
        if "en_state" in values:
            for rec in self.filtered(lambda x: x.en_state == "done"):
                if not rec.timesheet_ids.filtered(lambda x: x.en_state == "approved"):
                    raise ValidationError("Bạn không thể hoàn thành công việc khi chưa khai timesheet.")
        return res
