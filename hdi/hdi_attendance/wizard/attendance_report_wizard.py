# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AttendanceReportWizard(models.TransientModel):
    _name = 'attendance.report.wizard'
    _description = 'Wizard báo cáo chấm công'

    # Filter options
    report_type = fields.Selection([
        ('individual', 'Báo cáo cá nhân'),
        ('department', 'Báo cáo theo phòng ban'),
        ('company', 'Báo cáo toàn công ty'),
        ('summary', 'Báo cáo tổng hợp'),
    ], string='Loại báo cáo', required=True, default='individual')
    
    date_from = fields.Date(
        string='Từ ngày',
        required=True,
        default=lambda self: fields.Date.today().replace(day=1)
    )
    
    date_to = fields.Date(
        string='Đến ngày', 
        required=True,
        default=fields.Date.today
    )
    
    employee_ids = fields.Many2many(
        'hr.employee',
        string='Nhân viên',
        help='Để trống để lấy tất cả nhân viên'
    )
    
    department_ids = fields.Many2many(
        'hr.department',
        string='Phòng ban',
        help='Để trống để lấy tất cả phòng ban'
    )
    
    # Report options
    include_details = fields.Boolean(
        string='Bao gồm chi tiết',
        default=True,
        help='Hiển thị chi tiết từng lần chấm công'
    )
    
    include_summary = fields.Boolean(
        string='Bao gồm tổng kết',
        default=True,
        help='Hiển thị thống kê tổng hợp'
    )
    
    include_exceptions = fields.Boolean(
        string='Bao gồm ngoại lệ',
        default=True,
        help='Hiển thị các ngoại lệ chấm công'
    )
    
    output_format = fields.Selection([
        ('pdf', 'PDF'),
        ('xlsx', 'Excel'),
        ('csv', 'CSV'),
    ], string='Định dạng xuất', default='pdf')
    
    group_by = fields.Selection([
        ('employee', 'Nhân viên'),
        ('department', 'Phòng ban'),
        ('date', 'Ngày'),
        ('week', 'Tuần'),
        ('month', 'Tháng'),
    ], string='Nhóm theo', default='employee')

    @api.onchange('report_type')
    def _onchange_report_type(self):
        """Update domain based on report type"""
        if self.report_type == 'individual':
            self.employee_ids = [(6, 0, [self.env.user.employee_id.id])] if self.env.user.employee_id else False
        elif self.report_type == 'department':
            if self.env.user.employee_id and self.env.user.employee_id.department_id:
                self.department_ids = [(6, 0, [self.env.user.employee_id.department_id.id])]

    def action_generate_report(self):
        """Generate attendance report"""
        self.ensure_one()
        
        # Prepare domain
        domain = [
            ('check_in_date', '>=', self.date_from),
            ('check_in_date', '<=', self.date_to),
        ]
        
        if self.employee_ids:
            domain.append(('employee_id', 'in', self.employee_ids.ids))
        elif self.department_ids:
            employees = self.env['hr.employee'].search([
                ('department_id', 'in', self.department_ids.ids)
            ])
            domain.append(('employee_id', 'in', employees.ids))
        
        # Get attendance data
        attendances = self.env['hr.attendance'].search(domain)
        
        if not attendances:
            raise UserError(_('Không tìm thấy dữ liệu chấm công trong khoảng thời gian đã chọn!'))
        
        # Generate report based on format
        if self.output_format == 'pdf':
            return self._generate_pdf_report(attendances)
        elif self.output_format == 'xlsx':
            return self._generate_xlsx_report(attendances)
        else:  # csv
            return self._generate_csv_report(attendances)

    def _generate_pdf_report(self, attendances):
        """Generate PDF report"""
        data = {
            'attendances': attendances.ids,
            'form': self.read()[0],
            'date_from': self.date_from,
            'date_to': self.date_to,
        }
        
        return self.env.ref('hdi_attendance.report_attendance_summary').report_action(
            self, data=data
        )

    def _generate_xlsx_report(self, attendances):
        """Generate Excel report"""
        # This would require report_xlsx module
        raise UserError(_('Tính năng xuất Excel sẽ được bổ sung trong phiên bản tiếp theo.'))

    def _generate_csv_report(self, attendances):
        """Generate CSV report"""
        # This would generate CSV data
        raise UserError(_('Tính năng xuất CSV sẽ được bổ sung trong phiên bản tiếp theo.'))


class AttendanceBulkUpdateWizard(models.TransientModel):
    _name = 'attendance.bulk.update.wizard'
    _description = 'Wizard cập nhật hàng loạt chấm công'

    attendance_ids = fields.Many2many(
        'hr.attendance',
        string='Chấm công cần cập nhật',
        required=True
    )
    
    update_type = fields.Selection([
        ('work_shift', 'Ca làm việc'),
        ('work_location', 'Địa điểm làm việc'),
        ('add_explanation', 'Thêm giải trình'),
        ('approve_all', 'Duyệt tất cả'),
        ('correct_time', 'Sửa thời gian'),
    ], string='Loại cập nhật', required=True)
    
    # Fields for different update types
    new_work_shift = fields.Selection([
        ('morning', 'Ca sáng'),
        ('afternoon', 'Ca chiều'), 
        ('night', 'Ca tối'),
        ('full', 'Ca ngày'),
        ('flexible', 'Ca linh hoạt'),
    ], string='Ca làm việc mới')
    
    new_work_location_id = fields.Many2one(
        'hr.work.location',
        string='Địa điểm làm việc mới'
    )
    
    bulk_explanation = fields.Text(
        string='Giải trình cho tất cả'
    )
    
    time_adjustment_hours = fields.Float(
        string='Điều chỉnh thời gian (giờ)',
        help='Số giờ cần điều chỉnh (âm để trừ, dương để cộng)'
    )
    
    reason = fields.Text(
        string='Lý do cập nhật',
        required=True
    )

    def action_apply_updates(self):
        """Apply bulk updates"""
        self.ensure_one()
        
        if not self.attendance_ids:
            raise UserError(_('Vui lòng chọn ít nhất một bản ghi chấm công!'))
        
        updated_count = 0
        
        for attendance in self.attendance_ids:
            try:
                if self.update_type == 'work_shift' and self.new_work_shift:
                    attendance.hdi_work_shift = self.new_work_shift
                    updated_count += 1
                    
                elif self.update_type == 'work_location' and self.new_work_location_id:
                    attendance.hdi_work_location_id = self.new_work_location_id
                    updated_count += 1
                    
                elif self.update_type == 'add_explanation' and self.bulk_explanation:
                    self.env['attendance.explanation'].create({
                        'attendance_id': attendance.id,
                        'explanation': self.bulk_explanation,
                        'state': 'approved',
                        'approved_by': self.env.user.id,
                        'approved_date': fields.Datetime.now(),
                    })
                    updated_count += 1
                    
                elif self.update_type == 'correct_time' and self.time_adjustment_hours:
                    if attendance.check_in:
                        new_checkin = attendance.check_in + timedelta(hours=self.time_adjustment_hours)
                        attendance.check_in = new_checkin
                    if attendance.check_out:
                        new_checkout = attendance.check_out + timedelta(hours=self.time_adjustment_hours)
                        attendance.check_out = new_checkout
                    updated_count += 1
                
                # Add note about bulk update
                attendance.message_post(
                    body=_('Cập nhật hàng loạt: %s - %s') % (
                        dict(self._fields['update_type'].selection)[self.update_type],
                        self.reason
                    )
                )
                
            except Exception as e:
                # Log error but continue with other records
                continue
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Cập nhật thành công!'),
                'message': _('Đã cập nhật %d/%d bản ghi chấm công.') % (
                    updated_count, len(self.attendance_ids)
                ),
                'type': 'success',
                'sticky': False,
            }
        }