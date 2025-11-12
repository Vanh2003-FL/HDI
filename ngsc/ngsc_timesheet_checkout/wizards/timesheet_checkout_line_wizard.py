from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from datetime import date

class TimesheetCheckoutLineWizard(models.TransientModel):
    """
    Popup phụ giúp người dùng ghi nhanh 1 dòng timesheet thật.
    """
    _name = 'timesheet.checkout.line.wizard'
    _description = 'Popup ghi timesheet thật'

    task_id = fields.Many2one('project.task', string='Công việc', required=True, readonly=True)
    description = fields.Text(string='Mô tả')
    hours = fields.Float(string='Giờ')
    is_overtime = fields.Boolean(string='Tăng ca')
    parent_line_id = fields.Many2one('timesheet.checkout.line', string='Dòng cha')

    def action_save_line(self):
        """
        Ghi dòng timesheet vào bảng thật và cập nhật lại dòng tạm bên ngoài popup.
        """
        self.ensure_one()
        # ===== VALIDATION =====
        if not self.task_id:
            raise ValidationError("Bạn chưa chọn công việc.")

        if not self.description or not self.description.strip():
            raise ValidationError("Bạn chưa nhập mô tả công việc.")

        if self.hours is None:
            raise ValidationError("Bạn chưa nhập số giờ làm việc.")

        if self.hours <= 0:
            raise ValidationError("Số giờ phải lớn hơn 0.")

        employee = self.env.user.employee_id
        if not employee:
            raise ValidationError("Người dùng chưa được liên kết với nhân viên.")

        # Ghi dòng timesheet thật
        self.env['account.analytic.line'].create({
            'name': self.description or '/',
            'task_id': self.task_id.id,
            'project_id': self.task_id.project_id.id,
            'employee_id': employee.id,
            'user_id': self.env.uid,
            'unit_amount': self.hours,
            'is_overtime': self.is_overtime,
            'date': fields.Date.today(),
            'is_timesheet': True,
        })

        # Cập nhật lại dòng tạm ngoài màn hình chính
        if self.parent_line_id:
            self.parent_line_id.write({
                'description': self.description,
                'hours': self.hours,
                'is_overtime': self.is_overtime,
            })

        return {'type': 'ir.actions.act_window_close'}
