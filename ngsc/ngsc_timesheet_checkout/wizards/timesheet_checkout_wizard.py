# -*- coding: utf-8 -*-
# Đây là khai báo đầu file để hỗ trợ tiếng Việt và các ký tự Unicode.

# Nhúng các công cụ sẵn có của Odoo để làm việc với dữ liệu, giao diện, logic.
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from datetime import date

# =========================
# 1. WIZARD CHÍNH - FORM KHAI TIMESHEET
# =========================

class TimesheetCheckoutWizard(models.TransientModel):
    """
    Đây là mô hình 'tạm' (transient model), chỉ tồn tại trong quá trình xử lý,
    không lưu lâu dài vào cơ sở dữ liệu. Dùng làm màn hình pop-up yêu cầu người
    dùng khai báo công việc khi checkout.
    """
    _name = 'timesheet.checkout.wizard'
    _description = 'Timesheet Checkout Wizard'

    # Danh sách các dòng timesheet con (các task người dùng cần khai)
    line_ids = fields.One2many('timesheet.checkout.line', 'wizard_id', string='Danh sách task')

    # Cờ cho biết có bỏ qua kiểm tra 8h làm việc hay không (dành cho các trường hợp người dùng vẫn muốn checkout)
    skip_check = fields.Boolean(default=False)

    @api.model
    def default_get(self, fields_list):
        """
        Khi mở popup wizard, hệ thống tự tìm các task mà người dùng hiện tại đang xử lý
        và tạo sẵn dòng để người dùng dễ khai báo thời gian.
        """
        res = super().default_get(fields_list)

        # Tìm tất cả các task mà người dùng này đang là người phụ trách (PIC) và đang ở trạng thái 'Đang thực hiện'
        tasks = self.env['project.task'].search([
            ('en_handler', '=', self.env.user.id),
            ('stage_id.name', '=', 'Đang thực hiện')
        ])

        # Tạo danh sách dòng timesheet trống cho mỗi task tìm được
        lines = []
        for task in tasks:
            lines.append((0, 0, {
                'task_id': task.id,
                'description': '',
                'hours': 0.0,
            }))

        # Gán vào line_ids để hiển thị trên giao diện
        res['line_ids'] = lines
        return res

    def action_submit(self):
        """
        Khi người dùng nhấn nút "Lưu" trong popup:
        - Kiểm tra xem có dòng hợp lệ không (có task + số giờ > 0)
        - Nếu tổng số giờ chưa đủ 8h, mở cảnh báo
        - Nếu đủ điều kiện thì tạo các dòng timesheet thật sự và ghi nhận giờ checkout
        """
        self.ensure_one()  # Đảm bảo chỉ xử lý 1 wizard

        if not self.line_ids:
            raise ValidationError("Bạn chưa khai báo bất kỳ dòng timesheet nào.")

        # Lọc các dòng hợp lệ (có task và giờ > 0)
        valid_lines = self.line_ids.filtered(lambda l: l.task_id and l.hours > 0.0)
        # if not valid_lines:
        #     raise ValidationError("Bạn phải nhập ít nhất một dòng timesheet hợp lệ (có công việc và số giờ > 0).")

        Timesheet = self.env['account.analytic.line']
        employee = self.env.user.employee_id
        if not employee:
            raise ValidationError("Người dùng chưa được liên kết với nhân viên.")

        # Tính tổng giờ hôm nay (bao gồm cả các dòng timesheet đã có)
        today = date.today()
        total_hours_new = sum(valid_lines.mapped('hours'))

        existing_timesheets = Timesheet.search([
            ('user_id', '=', self.env.uid),
            ('date', '=', today.strftime('%Y-%m-%d'))
        ])
        total_existing_hours = sum(existing_timesheets.mapped('unit_amount'))
        total_hours = total_hours_new + total_existing_hours

        # Nếu tổng giờ chưa đủ 8 tiếng và người dùng chưa chọn "bỏ qua", thì mở cảnh báo
        if total_hours < 8.0 and not self.skip_check:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'timesheet.warning.wizard',
                'view_mode': 'form',
                'view_id': self.env.ref('ngsc_timesheet_checkout.view_timesheet_warning_wizard_form').id,
                'target': 'new',
                'context': dict(self.env.context, checkout_wizard_id=self.id),
            }

        # Ghi các dòng timesheet thật sự
        for line in valid_lines:
            Timesheet.create({
                'name': line.description or '/',
                'task_id': line.task_id.id,
                'project_id': line.task_id.project_id.id,
                'employee_id': employee.id,
                'user_id': self.env.uid,
                'unit_amount': line.hours,
                'date': fields.Date.today(),
            })

        # Ghi nhận giờ checkout cho nhân viên (nếu đang trong ca làm)
        attendance = self.env['hr.attendance'].search([
            ('employee_id.user_id', '=', self.env.uid),
            ('check_out', '=', False)
        ], limit=1)
        if attendance:
            attendance.check_out = fields.Datetime.now()

        # Reload lại màn hình chính để thấy kết quả
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.attendance',
            'view_mode': 'form',
            'target': 'new',
            'res_id': attendance.id if attendance else False,
        }

    def action_skip_and_checkout(self):
        """
        Skip working hours check and perform checkout for the employee.
        """
        self.ensure_one()
        self.skip_check = True
        self._checkout_employee()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def _checkout_employee(self):
        """Helper to perform checkout for the current employee."""
        attendance = self.env['hr.attendance'].search([
            ('employee_id.user_id', '=', self.env.uid),
            ('check_out', '=', False)
        ], limit=1)
        if attendance:
            attendance.check_out = fields.Datetime.now()

    def action_close_popup(self):
        """
        Khi người dùng chọn đóng popup (không khai báo gì), vẫn cho phép checkout.
        """
        self.ensure_one()
        self.skip_check = True
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_send_approval(self):
        """
        Chức năng 'Gửi duyệt' timesheet.
        Dành cho người dùng không muốn tự ghi ngay mà gửi lên cho cấp trên duyệt.
        """
        AnalyticLine = self.env['account.analytic.line']

        for wizard in self:
            has_valid_line = False

            for line in wizard.line_ids:
                if not line.task_id or line.hours == 0.0:
                    continue

                has_valid_line = True

                # Ghi dòng timesheet thật
                AnalyticLine.create({
                    'name': line.description or '/',
                    'project_id': line.task_id.project_id.id,
                    'task_id': line.task_id.id,
                    'user_id': self.env.uid,
                    'employee_id': self.env.user.employee_id.id,
                    'unit_amount': line.hours,
                    'date': fields.Date.today(),
                })

            if not has_valid_line:
                raise UserError("Bạn cần khai báo ít nhất một dòng timesheet trước khi gửi duyệt.")

        return None


# =========================
# 2. DÒNG CHI TIẾT TRONG FORM POPUP
# =========================


# =========================
# 3. POPUP PHỤ GHI NHANH
# =========================
