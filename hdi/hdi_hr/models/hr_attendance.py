# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from pytz import timezone, UTC
import logging

_logger = logging.getLogger(__name__)


class HrAttendance(models.Model):
    _name = 'hr.attendance'
    _inherit = ['hr.attendance', 'mail.thread', 'mail.activity.mixin']

    hdi_work_shift = fields.Selection([
        ('morning', 'Ca sáng'),
        ('afternoon', 'Ca chiều'),
        ('night', 'Ca tối'),
        ('full', 'Ca ngày'),
    ], string='Ca làm việc', default='full')
    
    hdi_is_overtime = fields.Boolean(
        string='Tăng ca',
        default=False
    )
    
    hdi_location = fields.Char(
        string='Địa điểm',
        help='Địa điểm chấm công'
    )
    
    # Computed fields for My Attendance views
    check_in_date = fields.Date(
        string='Ngày check-in',
        compute='_compute_check_in_date',
        store=True
    )
    
    check_out_date = fields.Date(
        string='Ngày check-out',
        compute='_compute_check_out_date',
        store=True
    )
    
    hdi_day_of_week = fields.Char(
        string='Thứ',
        compute='_compute_day_of_week',
        store=True
    )
    
    # Status fields
    hdi_is_late = fields.Boolean(
        string='Đi muộn',
        compute='_compute_attendance_status',
        store=True
    )
    
    hdi_is_early_leave = fields.Boolean(
        string='Về sớm',
        compute='_compute_attendance_status',
        store=True
    )
    
    hdi_is_missing_checkout = fields.Boolean(
        string='Thiếu checkout',
        compute='_compute_attendance_status',
        store=True
    )
    
    hdi_late_minutes = fields.Float(
        string='Số phút đi muộn',
        compute='_compute_attendance_status',
        store=True
    )
    
    hdi_early_leave_minutes = fields.Float(
        string='Số phút về sớm',
        compute='_compute_attendance_status',
        store=True
    )
    
    hdi_check_in_status = fields.Char(
        string='Trạng thái check-in',
        compute='_compute_attendance_status',
        store=True
    )
    
    hdi_check_out_status = fields.Char(
        string='Trạng thái check-out',
        compute='_compute_attendance_status',
        store=True
    )
    
    # Working hours
    hdi_expected_hours = fields.Float(
        string='Giờ làm việc quy định',
        compute='_compute_expected_hours',
        store=True
    )
    
    hdi_overtime_hours = fields.Float(
        string='Giờ làm thêm',
        compute='_compute_overtime_hours',
        store=True
    )
    
    # Color for calendar view
    color = fields.Integer(
        string='Màu',
        compute='_compute_color',
        store=True
    )
    
    # Explanation related
    hdi_explanation_ids = fields.One2many(
        'hr.attendance.explanation',
        'attendance_id',
        string='Giải trình'
    )
    
    hdi_explanation_count = fields.Integer(
        string='Số lần giải trình',
        compute='_compute_explanation_count'
    )
    
    hdi_can_explain = fields.Boolean(
        string='Có thể giải trình',
        compute='_compute_can_explain'
    )
    
    hdi_attendance_state = fields.Selection([
        ('normal', 'Bình thường'),
        ('late', 'Đi muộn'),
        ('early_leave', 'Về sớm'),
        ('missing_checkout', 'Thiếu checkout'),
        ('explained', 'Đã giải trình'),
    ], string='Trạng thái', compute='_compute_attendance_state', store=True)
    
    @api.depends('check_in', 'employee_id')
    def _compute_check_in_date(self):
        """Tính ngày check-in theo timezone của nhân viên"""
        for rec in self:
            if rec.check_in:
                tz = timezone(rec.employee_id.tz or self.env.user.tz or 'Asia/Ho_Chi_Minh')
                check_in_local = rec.check_in.replace(tzinfo=UTC).astimezone(tz)
                rec.check_in_date = check_in_local.date()
            else:
                rec.check_in_date = False
    
    @api.depends('check_out', 'employee_id')
    def _compute_check_out_date(self):
        """Tính ngày check-out theo timezone của nhân viên"""
        for rec in self:
            if rec.check_out:
                tz = timezone(rec.employee_id.tz or self.env.user.tz or 'Asia/Ho_Chi_Minh')
                check_out_local = rec.check_out.replace(tzinfo=UTC).astimezone(tz)
                rec.check_out_date = check_out_local.date()
            else:
                rec.check_out_date = False
    
    @api.depends('check_in_date')
    def _compute_day_of_week(self):
        """Tính thứ trong tuần"""
        day_names = ['Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'Chủ nhật']
        for rec in self:
            if rec.check_in_date:
                weekday = rec.check_in_date.weekday()
                rec.hdi_day_of_week = day_names[weekday]
            else:
                rec.hdi_day_of_week = ''
    
    @api.depends('check_in', 'check_out', 'employee_id')
    def _compute_attendance_status(self):
        """Tính trạng thái chấm công - simplified version"""
        for rec in self:
            rec.hdi_is_late = False
            rec.hdi_is_early_leave = False
            rec.hdi_is_missing_checkout = not rec.check_out if rec.check_in else False
            rec.hdi_late_minutes = 0.0
            rec.hdi_early_leave_minutes = 0.0
            rec.hdi_check_in_status = 'Bình thường' if rec.check_in else 'Chưa check-in'
            rec.hdi_check_out_status = 'Bình thường' if rec.check_out else 'Chưa check-out'
    
    @api.depends('employee_id', 'check_in_date')
    def _compute_expected_hours(self):
        """Tính số giờ làm việc quy định"""
        for rec in self:
            rec.hdi_expected_hours = 8.0  # Default 8 hours
    
    @api.depends('worked_hours', 'hdi_expected_hours')
    def _compute_overtime_hours(self):
        """Tính số giờ làm thêm"""
        for rec in self:
            if rec.worked_hours > rec.hdi_expected_hours:
                rec.hdi_overtime_hours = rec.worked_hours - rec.hdi_expected_hours
            else:
                rec.hdi_overtime_hours = 0.0
    
    @api.depends('hdi_is_late', 'hdi_is_early_leave', 'hdi_is_missing_checkout')
    def _compute_color(self):
        """Tính màu hiển thị"""
        for rec in self:
            if rec.hdi_is_late or rec.hdi_is_early_leave:
                rec.color = 1  # Red
            elif rec.hdi_is_missing_checkout:
                rec.color = 3  # Yellow
            else:
                rec.color = 10  # Green
    
    @api.depends('hdi_explanation_ids')
    def _compute_explanation_count(self):
        """Đếm số lần giải trình"""
        for rec in self:
            rec.hdi_explanation_count = len(rec.hdi_explanation_ids)
    
    @api.depends('hdi_is_late', 'hdi_is_early_leave', 'hdi_is_missing_checkout')
    def _compute_can_explain(self):
        """Kiểm tra xem có thể giải trình không"""
        for rec in self:
            rec.hdi_can_explain = rec.hdi_is_late or rec.hdi_is_early_leave or rec.hdi_is_missing_checkout
    
    @api.depends('hdi_is_late', 'hdi_is_early_leave', 'hdi_is_missing_checkout', 'hdi_explanation_count')
    def _compute_attendance_state(self):
        """Tính trạng thái tổng thể"""
        for rec in self:
            if rec.hdi_explanation_count > 0:
                rec.hdi_attendance_state = 'explained'
            elif rec.hdi_is_missing_checkout:
                rec.hdi_attendance_state = 'missing_checkout'
            elif rec.hdi_is_late:
                rec.hdi_attendance_state = 'late'
            elif rec.hdi_is_early_leave:
                rec.hdi_attendance_state = 'early_leave'
            else:
                rec.hdi_attendance_state = 'normal'
    
    def action_create_explanation(self):
        """Tạo giải trình chấm công"""
        self.ensure_one()
        return {
            'name': _('Giải trình chấm công'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.attendance.explanation',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_attendance_id': self.id,
                'default_employee_id': self.employee_id.id,
                'default_explanation_date': self.check_in_date,
            }
        }
    
    def action_view_explanations(self):
        """Xem danh sách giải trình"""
        self.ensure_one()
        return {
            'name': _('Giải trình chấm công'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.attendance.explanation',
            'view_mode': 'list,form',
            'domain': [('attendance_id', '=', self.id)],
        }
