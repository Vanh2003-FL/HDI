# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    # === BASIC FIELDS ===
    note = fields.Text(string='Ghi chú')
    work_location_id = fields.Many2one(
        'hr.work.location',
        string='Địa điểm làm việc',
        related='employee_id.work_location_id',
        store=True
    )
    
    # === DATE/TIME FIELDS ===
    check_in_date = fields.Date(
        string='Ngày check in',
        compute='_compute_check_in_date',
        store=True
    )
    
    check_in_time = fields.Float(
        string='Giờ check in',
        compute='_compute_check_in_date',
        store=True
    )
    
    check_out_date = fields.Date(
        string='Ngày check out',
        compute='_compute_check_out_date',
        store=True
    )
    
    check_out_time = fields.Float(
        string='Giờ check out',
        compute='_compute_check_out_date',
        store=True
    )
    
    date = fields.Date(
        string='Ngày',
        compute='_compute_check_in_date',
        store=True,
        index=True
    )
    
    # === DETECTION FIELDS ===
    en_missing_attendance = fields.Boolean(
        string='Thiếu chấm công',
        default=False,
        help='Đánh dấu nếu thiếu check in hoặc check out'
    )
    
    en_late = fields.Boolean(
        string='Đi muộn',
        compute='_compute_en_late',
        store=True
    )
    
    en_soon = fields.Boolean(
        string='Về sớm',
        compute='_compute_en_soon',
        store=True
    )
    
    late_minutes = fields.Float(
        string='Số phút đi muộn',
        compute='_compute_en_late',
        store=True
    )
    
    early_leave_minutes = fields.Float(
        string='Số phút về sớm',
        compute='_compute_en_soon',
        store=True
    )
    
    # === EXPLANATION ===
    explanation_required = fields.Boolean(
        string='Cần giải trình',
        compute='_compute_explanation_required',
        store=True
    )
    
    explanation_id = fields.Many2one(
        'hr.attendance.explanation',
        string='Giải trình',
        readonly=True
    )
    
    explanation_count = fields.Integer(
        string='Số lần giải trình',
        compute='_compute_explanation_count'
    )
    
    explanation_month_count = fields.Integer(
        string='Số lần giải trình trong tháng',
        compute='_compute_explanation_month_count'
    )
    
    # === UI FIELDS ===
    color = fields.Integer(
        string="Màu",
        compute='_compute_color',
        store=False
    )
    
    warning_message = fields.Text(
        string='Cảnh báo',
        compute='_compute_color'
    )
    
    # === COMPUTED METHODS ===
    @api.depends('check_in')
    def _compute_check_in_date(self):
        """Tính ngày và giờ check in"""
        for rec in self:
            if rec.check_in:
                # Convert to employee timezone
                tz = rec.employee_id.tz or 'Asia/Ho_Chi_Minh'
                check_in_tz = rec.check_in
                
                rec.check_in_date = check_in_tz.date()
                rec.date = check_in_tz.date()
                rec.check_in_time = check_in_tz.hour + check_in_tz.minute / 60.0
            else:
                rec.check_in_date = False
                rec.date = False
                rec.check_in_time = 0.0
    
    @api.depends('check_out')
    def _compute_check_out_date(self):
        """Tính ngày và giờ check out"""
        for rec in self:
            if rec.check_out:
                check_out_tz = rec.check_out
                rec.check_out_date = check_out_tz.date()
                rec.check_out_time = check_out_tz.hour + check_out_tz.minute / 60.0
            else:
                rec.check_out_date = False
                rec.check_out_time = 0.0
    
    @api.depends('check_in', 'employee_id')
    def _compute_en_late(self):
        """Phát hiện đi muộn dựa trên lịch làm việc"""
        for rec in self:
            rec.en_late = False
            rec.late_minutes = 0.0
            
            if not rec.check_in or not rec.employee_id:
                continue
            
            # Get employee calendar
            calendar = rec.employee_id.resource_calendar_id
            if not calendar:
                continue
            
            # Get expected start time from calendar
            check_in_date = rec.check_in.date()
            weekday = rec.check_in.weekday()
            
            # Find calendar attendance for this day
            calendar_attendance = calendar.attendance_ids.filtered(
                lambda a: int(a.dayofweek) == weekday
            ).sorted('hour_from')
            
            if calendar_attendance:
                expected_start = calendar_attendance[0].hour_from
                actual_start = rec.check_in_time
                
                # Allow 15 minutes grace period
                grace_minutes = 15
                if actual_start > expected_start + (grace_minutes / 60.0):
                    rec.en_late = True
                    rec.late_minutes = (actual_start - expected_start) * 60
    
    @api.depends('check_out', 'employee_id')
    def _compute_en_soon(self):
        """Phát hiện về sớm"""
        for rec in self:
            rec.en_soon = False
            rec.early_leave_minutes = 0.0
            
            if not rec.check_out or not rec.employee_id:
                continue
            
            calendar = rec.employee_id.resource_calendar_id
            if not calendar:
                continue
            
            weekday = rec.check_out.weekday()
            calendar_attendance = calendar.attendance_ids.filtered(
                lambda a: int(a.dayofweek) == weekday
            ).sorted('hour_to', reverse=True)
            
            if calendar_attendance:
                expected_end = calendar_attendance[0].hour_to
                actual_end = rec.check_out_time
                
                # Allow 15 minutes grace period
                grace_minutes = 15
                if actual_end < expected_end - (grace_minutes / 60.0):
                    rec.en_soon = True
                    rec.early_leave_minutes = (expected_end - actual_end) * 60
    
    @api.depends('en_missing_attendance', 'en_late', 'en_soon', 'explanation_id')
    def _compute_explanation_required(self):
        """Xác định cần giải trình"""
        for rec in self:
            rec.explanation_required = (
                rec.en_missing_attendance or
                rec.en_late or
                rec.en_soon or
                not rec.check_out
            ) and not rec.explanation_id
    
    def _compute_explanation_count(self):
        """Đếm số lần giải trình"""
        for rec in self:
            rec.explanation_count = self.env['hr.attendance.explanation'].search_count([
                ('employee_id', '=', rec.employee_id.id),
                ('hr_attendance_id', '=', rec.id),
            ])
    
    def _compute_explanation_month_count(self):
        """Đếm số lần giải trình trong tháng"""
        for rec in self:
            if rec.check_in:
                month_start = rec.check_in.replace(day=1)
                month_end = (month_start + relativedelta(months=1)) - timedelta(days=1)
                
                rec.explanation_month_count = self.env['hr.attendance.explanation'].search_count([
                    ('employee_id', '=', rec.employee_id.id),
                    ('explanation_date', '>=', month_start.date()),
                    ('explanation_date', '<=', month_end.date()),
                ])
            else:
                rec.explanation_month_count = 0
    
    @api.depends('en_missing_attendance', 'en_late', 'en_soon', 'date', 'employee_id', 'worked_hours')
    def _compute_color(self):
        """Tính màu hiển thị và warning message"""
        for rec in self:
            color = 10  # Green - OK
            warnings = []
            
            # Check missing checkout
            if not rec.check_out:
                color = 1  # Red
                warnings.append('Thiếu checkout')
            
            # Check late
            if rec.en_late:
                color = 1
                warnings.append(f'Đi muộn {rec.late_minutes:.0f} phút')
            
            # Check early leave
            if rec.en_soon:
                color = 1
                warnings.append(f'Về sớm {rec.early_leave_minutes:.0f} phút')
            
            # Check worked hours
            if rec.worked_hours < 7.75 and rec.check_out:
                # Check if has leave
                has_leave = self.env['hr.leave'].search_count([
                    ('employee_id', '=', rec.employee_id.id),
                    ('state', '=', 'validate'),
                    ('request_date_from', '<=', rec.date),
                    ('request_date_to', '>=', rec.date),
                ])
                
                if not has_leave:
                    if color == 10:
                        color = 1
                    warnings.append('Không đủ giờ công')
            
            # Check if has explanation
            if warnings and rec.explanation_id and rec.explanation_id.state == 'approved':
                color = 10
                warnings = ['Đã giải trình']
            
            rec.color = color
            rec.warning_message = '\n'.join(warnings) if warnings else ''
    
    # === CRUD OVERRIDES ===
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to send notifications"""
        res = super().create(vals_list)
        res.notify_soon_late()
        return res
    
    def write(self, vals):
        """Override write to update notifications"""
        res = super().write(vals)
        if 'check_in' in vals or 'check_out' in vals or 'employee_id' in vals:
            self.notify_soon_late()
        return res
    
    def notify_soon_late(self):
        """Gửi thông báo nếu đi muộn/về sớm"""
        for rec in self:
            if rec.en_late or rec.en_soon:
                message = []
                if rec.en_late:
                    message.append(f'Đi muộn {rec.late_minutes:.0f} phút')
                if rec.en_soon:
                    message.append(f'Về sớm {rec.early_leave_minutes:.0f} phút')
                
                rec.message_post(
                    body=' - '.join(message),
                    subject='Cảnh báo chấm công',
                    partner_ids=rec.employee_id.user_id.partner_id.ids,
                    message_type='notification',
                )
    
    # === ACTIONS ===
    def button_create_explanation(self):
        """Tạo giải trình chấm công"""
        self.ensure_one()
        return {
            'name': _('Giải trình chấm công'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.attendance.explanation',
            'view_mode': 'form',
            'context': {
                'default_hr_attendance_id': self.id,
                'default_employee_id': self.employee_id.id,
                'default_explanation_date': self.date or fields.Date.today(),
            },
            'target': 'new',
        }
    
    def button_create_hr_leave(self):
        """Tạo đơn nghỉ phép"""
        self.ensure_one()
        return {
            'name': _('Tạo đơn nghỉ phép'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.leave',
            'view_mode': 'form',
            'context': {
                'default_employee_id': self.employee_id.id,
                'default_request_date_from': self.date,
                'default_request_date_to': self.date,
            },
            'target': 'new',
        }
    
    # === CRON JOBS ===
    @api.model
    def auto_log_out_job(self):
        """Cron job: Tự động checkout cho những người quên checkout"""
        yesterday = fields.Date.today() - timedelta(days=1)
        
        # Find attendances without checkout from yesterday
        attendances = self.search([
            ('check_in', '>=', fields.Datetime.to_string(
                datetime.combine(yesterday, datetime.min.time())
            )),
            ('check_in', '<=', fields.Datetime.to_string(
                datetime.combine(yesterday, datetime.max.time())
            )),
            ('check_out', '=', False),
        ])
        
        for att in attendances:
            # Auto checkout at 18:00
            auto_checkout_time = datetime.combine(yesterday, datetime.min.time()) + timedelta(hours=18)
            att.write({
                'check_out': auto_checkout_time,
                'en_missing_attendance': True,
            })
            
            _logger.info(f'Auto checkout for employee {att.employee_id.name} at {auto_checkout_time}')
        
        return len(attendances)
    
    # === HELPER METHODS ===
    def name_get(self):
        """Custom name_get"""
        result = []
        for rec in self:
            if rec.check_in:
                name = f"{rec.employee_id.name} - {rec.check_in.strftime('%d/%m/%Y %H:%M')}"
                if rec.check_out:
                    name += f" → {rec.check_out.strftime('%H:%M')}"
                result.append((rec.id, name))
            else:
                result.append((rec.id, rec.employee_id.name))
        return result
