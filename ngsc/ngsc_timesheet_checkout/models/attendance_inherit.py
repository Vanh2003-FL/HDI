from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'  # Kế thừa từ mô hình chấm công chuẩn của Odoo

    @api.model
    def attendance_manual(self, employee_id, action, context=None):
        # Lấy thông tin employee đang thao tác
        employee = self.env['hr.employee'].browse(employee_id)

        # Nếu nhân viên đang trong trạng thái "checked_in", nghĩa là đang làm và chuẩn bị "checkout"
        if employee.attendance_state == 'checked_in':
            today = fields.Date.today()  # Ngày hiện tại

            # Tìm các dòng timesheet đã khai hôm nay của user tương ứng, chỉ tính dòng thật (`is_timesheet=True`)
            timesheets = self.env['account.analytic.line'].search([
                ('user_id', '=', employee.user_id.id),
                ('date', '=', today),
                ('is_timesheet', '=', True),
            ])
            total_hours = sum(timesheets.mapped('unit_amount'))  # Tổng giờ đã khai hôm nay

            if total_hours < 8.0:
                # Nếu chưa đủ 8h → tìm task "In Progress" mà user đó là PIC (user_ids), deadline còn hiệu lực, có cha
                task = self.env['project.task'].search([
                    ('user_ids', 'in', employee.user_id.id),  # Là người chịu trách nhiệm (PIC)
                    ('stage_id.name', '=', 'In Progress'),    # Đang thực hiện
                    '|', ('date_deadline', '=', False),       # Không có hạn hoặc hạn còn hiệu lực
                         ('date_deadline', '>=', today),
                    ('parent_id', '!=', False),               # Là subtask (có cha)
                ], limit=1)

                if not task:
                    # Nếu không có task hợp lệ → báo lỗi
                    raise UserError(_("Bạn đang không có task cần thực hiện hôm nay để khai timesheet."))

                # Nếu có task → ghi nhanh 1 giờ timesheet vào task đó
                self.env['account.analytic.line'].create({
                    'name': f'Timesheet khi checkout',
                    'project_id': task.project_id.id,
                    'task_id': task.id,
                    'user_id': employee.user_id.id,
                    'employee_id': employee.id,
                    'unit_amount': 1.0,
                    'date': today,
                    'is_timesheet': True,
                })

                # Trả về thông báo kiểu Odoo khi thành công
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Checkout thành công'),
                        'message': f"Đã ghi 1 giờ timesheet vào task: {task.name}",
                        'type': 'success',
                        'sticky': False,
                    }
                }

        # Nếu không trong trạng thái 'checked_in' → gọi lại logic gốc của Odoo
        return super().attendance_manual(employee_id, action, context=context)
