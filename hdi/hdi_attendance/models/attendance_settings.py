# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class AttendanceSettings(models.Model):
    _name = 'attendance.settings'
    _description = 'Cài đặt chấm công'
    _rec_name = 'name'

    name = fields.Char(
        string='Tên cài đặt',
        required=True,
        default='Cài đặt chấm công'
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Công ty',
        default=lambda self: self.env.company
    )
    
    # Location settings
    enforce_location_checkin = fields.Boolean(
        string='Bắt buộc vị trí khi check-in',
        default=True,
        help='Bắt buộc nhân viên phải ở gần địa điểm làm việc khi check-in'
    )
    
    enforce_location_checkout = fields.Boolean(
        string='Bắt buộc vị trí khi check-out',
        default=False,
        help='Bắt buộc nhân viên phải ở gần địa điểm làm việc khi check-out'
    )
    
    max_checkin_distance = fields.Float(
        string='Khoảng cách tối đa check-in (m)',
        default=100.0,
        help='Khoảng cách tối đa cho phép khi check-in (mét)'
    )
    
    max_checkout_distance = fields.Float(
        string='Khoảng cách tối đa check-out (m)',
        default=500.0,
        help='Khoảng cách tối đa cho phép khi check-out (mét)'
    )
    
    # Time settings
    late_tolerance_minutes = fields.Integer(
        string='Dung sai đi muộn (phút)',
        default=15,
        help='Số phút dung sai trước khi coi là đi muộn'
    )
    
    early_leave_tolerance_minutes = fields.Integer(
        string='Dung sai về sớm (phút)',
        default=15,
        help='Số phút dung sai trước khi coi là về sớm'
    )
    
    auto_checkout_hours = fields.Float(
        string='Tự động check-out sau (giờ)',
        default=12.0,
        help='Tự động check-out sau số giờ làm việc (0 = không tự động)'
    )
    
    # Working hours settings
    standard_working_hours = fields.Float(
        string='Giờ làm việc tiêu chuẩn/ngày',
        default=8.0,
        help='Số giờ làm việc tiêu chuẩn trong 1 ngày'
    )
    
    overtime_threshold_hours = fields.Float(
        string='Ngưỡng tăng ca (giờ)',
        default=8.0,
        help='Số giờ làm việc tối thiểu để được tính tăng ca'
    )
    
    max_working_hours_per_day = fields.Float(
        string='Số giờ làm việc tối đa/ngày',
        default=12.0,
        help='Số giờ làm việc tối đa cho phép trong 1 ngày'
    )
    
    # Break time settings
    lunch_break_duration = fields.Float(
        string='Thời gian nghỉ trưa (giờ)',
        default=1.0,
        help='Thời gian nghỉ trưa (được trừ khỏi giờ làm việc)'
    )
    
    auto_deduct_break = fields.Boolean(
        string='Tự động trừ nghỉ trưa',
        default=True,
        help='Tự động trừ thời gian nghỉ trưa khỏi giờ làm việc'
    )
    
    # Notification settings
    notify_missing_checkin = fields.Boolean(
        string='Thông báo thiếu check-in',
        default=True,
        help='Gửi thông báo khi nhân viên quên check-in'
    )
    
    notify_missing_checkout = fields.Boolean(
        string='Thông báo thiếu check-out',
        default=True,
        help='Gửi thông báo khi nhân viên quên check-out'
    )
    
    notify_late_checkin = fields.Boolean(
        string='Thông báo đi muộn',
        default=True,
        help='Gửi thông báo khi nhân viên đi muộn'
    )
    
    notify_early_checkout = fields.Boolean(
        string='Thông báo về sớm',
        default=True,
        help='Gửi thông báo khi nhân viên về sớm'
    )
    
    # Explanation settings
    allow_explanation = fields.Boolean(
        string='Cho phép giải trình',
        default=True,
        help='Cho phép nhân viên giải trình các vấn đề chấm công'
    )
    
    explanation_deadline_days = fields.Integer(
        string='Hạn giải trình (ngày)',
        default=3,
        help='Số ngày tối đa để giải trình sau khi có vấn đề chấm công'
    )
    
    require_manager_approval = fields.Boolean(
        string='Yêu cầu duyệt của quản lý',
        default=True,
        help='Yêu cầu quản lý duyệt các giải trình chấm công'
    )
    
    # Rounding settings
    round_attendance_time = fields.Boolean(
        string='Làm tròn thời gian chấm công',
        default=False,
        help='Làm tròn thời gian check-in/out theo qui định'
    )
    
    rounding_minutes = fields.Selection([
        ('5', '5 phút'),
        ('10', '10 phút'),
        ('15', '15 phút'),
        ('30', '30 phút'),
    ], string='Làm tròn theo', default='15')
    
    # IP restriction settings
    enable_ip_restriction = fields.Boolean(
        string='Giới hạn IP',
        default=False,
        help='Chỉ cho phép chấm công từ các IP được phép'
    )
    
    allowed_ip_addresses = fields.Text(
        string='IP được phép',
        help='Danh sách IP được phép chấm công (mỗi IP một dòng)'
    )
    
    # Mobile app settings
    enable_mobile_checkin = fields.Boolean(
        string='Cho phép chấm công qua mobile',
        default=True,
        help='Cho phép chấm công qua ứng dụng di động'
    )
    
    require_photo_checkin = fields.Boolean(
        string='Bắt buộc chụp ảnh khi check-in',
        default=False,
        help='Bắt buộc chụp ảnh selfie khi check-in qua mobile'
    )
    
    # Kiosk settings
    enable_kiosk_mode = fields.Boolean(
        string='Cho phép chế độ kiosk',
        default=False,
        help='Cho phép chấm công qua máy kiosk/tablet'
    )
    
    kiosk_pin_required = fields.Boolean(
        string='Yêu cầu PIN cho kiosk',
        default=True,
        help='Yêu cầu nhập PIN khi chấm công qua kiosk'
    )

    @api.model
    def get_settings(self):
        """Lấy cài đặt chấm công hiện tại"""
        company = self.env.company
        settings = self.search([('company_id', '=', company.id)], limit=1)
        if not settings:
            settings = self.create({'company_id': company.id})
        return settings

    @api.model
    def create(self, vals):
        """Đảm bảo chỉ có 1 bản ghi cài đặt cho mỗi công ty"""
        company_id = vals.get('company_id', self.env.company.id)
        existing = self.search([('company_id', '=', company_id)])
        if existing:
            return existing.write(vals) and existing
        return super().create(vals)

    def get_working_hours_config(self):
        """Lấy cấu hình giờ làm việc"""
        return {
            'standard_hours': self.standard_working_hours,
            'overtime_threshold': self.overtime_threshold_hours,
            'max_hours_per_day': self.max_working_hours_per_day,
            'lunch_break': self.lunch_break_duration if self.auto_deduct_break else 0.0,
        }

    def get_tolerance_config(self):
        """Lấy cấu hình dung sai"""
        return {
            'late_tolerance': self.late_tolerance_minutes,
            'early_leave_tolerance': self.early_leave_tolerance_minutes,
        }

    def get_location_config(self):
        """Lấy cấu hình địa điểm"""
        return {
            'enforce_checkin': self.enforce_location_checkin,
            'enforce_checkout': self.enforce_location_checkout,
            'max_checkin_distance': self.max_checkin_distance,
            'max_checkout_distance': self.max_checkout_distance,
        }

    def get_notification_config(self):
        """Lấy cấu hình thông báo"""
        return {
            'notify_missing_checkin': self.notify_missing_checkin,
            'notify_missing_checkout': self.notify_missing_checkout,
            'notify_late_checkin': self.notify_late_checkin,
            'notify_early_checkout': self.notify_early_checkout,
        }