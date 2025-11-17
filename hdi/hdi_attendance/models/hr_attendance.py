# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from pytz import timezone, UTC
import pytz
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_round
from odoo.addons.resource.models.resource import float_to_time

_logger = logging.getLogger(__name__)


class HrAttendance(models.Model):
    _name = 'hr.attendance'
    _inherit = ['hr.attendance', 'mail.thread', 'mail.activity.mixin']
    _description = 'HDI Employee Attendance'

    # Basic fields extension
    hdi_work_shift = fields.Selection([
        ('morning', 'Ca sáng (6:00-14:00)'),
        ('afternoon', 'Ca chiều (14:00-22:00)'),
        ('night', 'Ca tối (22:00-6:00)'),
        ('full', 'Ca ngày (8:00-17:00)'),
        ('flexible', 'Ca linh hoạt'),
    ], string='Ca làm việc', default='full', tracking=True)
    
    hdi_work_location_id = fields.Many2one(
        'hr.work.location', 
        string='Địa điểm làm việc',
        help='Địa điểm làm việc khi check-in'
    )
    
    hdi_checkout_location_id = fields.Many2one(
        'hr.work.location', 
        string='Địa điểm check-out',
        help='Địa điểm làm việc khi check-out'
    )
    
    # GPS Coordinates
    check_in_latitude = fields.Float(
        string='Check-in Latitude',
        digits=(10, 7)
    )
    check_in_longitude = fields.Float(
        string='Check-in Longitude', 
        digits=(10, 7)
    )
    check_out_latitude = fields.Float(
        string='Check-out Latitude',
        digits=(10, 7)
    )
    check_out_longitude = fields.Float(
        string='Check-out Longitude',
        digits=(10, 7)
    )
    
    # Address computation
    check_in_address = fields.Char(
        string='Địa chỉ check-in',
        compute='_compute_address',
        store=True
    )
    check_out_address = fields.Char(
        string='Địa chỉ check-out', 
        compute='_compute_address',
        store=True
    )
    
    # Distance validation
    check_in_distance = fields.Float(
        string='Khoảng cách check-in (m)',
        compute='_compute_distance',
        store=True,
        help='Khoảng cách từ vị trí check-in đến địa điểm làm việc'
    )
    check_out_distance = fields.Float(
        string='Khoảng cách check-out (m)',
        compute='_compute_distance',
        store=True,
        help='Khoảng cách từ vị trí check-out đến địa điểm làm việc'
    )
    
    # Computed fields for date/time
    check_in_date = fields.Date(
        string='Ngày check-in',
        compute='_compute_check_in_date',
        store=True,
        index=True
    )
    
    check_out_date = fields.Date(
        string='Ngày check-out',
        compute='_compute_check_out_date',
        store=True
    )
    
    check_in_time = fields.Float(
        string='Giờ check-in',
        compute='_compute_check_in_time',
        store=True
    )
    
    check_out_time = fields.Float(
        string='Giờ check-out',
        compute='_compute_check_out_time', 
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
        string='Thiếu check-out',
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
    
    # Explanation related
    hdi_explanation_ids = fields.One2many(
        'attendance.explanation',
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
    
    # Color for calendar view
    color = fields.Integer(
        string='Màu',
        compute='_compute_color',
        store=True
    )
    
    # Note field
    note = fields.Text(string='Ghi chú')

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

    @api.depends('check_in', 'employee_id')
    def _compute_check_in_time(self):
        """Tính giờ check-in theo timezone của nhân viên"""
        for rec in self:
            if rec.check_in:
                tz = timezone(rec.employee_id.tz or self.env.user.tz or 'Asia/Ho_Chi_Minh')
                check_in_local = rec.check_in.replace(tzinfo=UTC).astimezone(tz)
                rec.check_in_time = check_in_local.hour + check_in_local.minute / 60.0
            else:
                rec.check_in_time = 0.0

    @api.depends('check_out', 'employee_id')
    def _compute_check_out_time(self):
        """Tính giờ check-out theo timezone của nhân viên"""
        for rec in self:
            if rec.check_out:
                tz = timezone(rec.employee_id.tz or self.env.user.tz or 'Asia/Ho_Chi_Minh')
                check_out_local = rec.check_out.replace(tzinfo=UTC).astimezone(tz)
                rec.check_out_time = check_out_local.hour + check_out_local.minute / 60.0
            else:
                rec.check_out_time = 0.0

    @api.depends('check_in_latitude', 'check_in_longitude', 'check_out_latitude', 'check_out_longitude')
    def _compute_address(self):
        """Tính địa chỉ từ GPS coordinates"""
        for rec in self:
            rec.check_in_address = ""
            rec.check_out_address = ""
            # TODO: Implement reverse geocoding if needed
            
    @api.depends(
        'check_in_latitude', 'check_in_longitude', 'hdi_work_location_id',
        'check_out_latitude', 'check_out_longitude', 'hdi_checkout_location_id'
    )
    def _compute_distance(self):
        """Tính khoảng cách từ GPS coordinates đến địa điểm làm việc"""
        for rec in self:
            rec.check_in_distance = 0.0
            rec.check_out_distance = 0.0
            
            # Calculate check-in distance
            if (rec.check_in_latitude and rec.check_in_longitude and 
                rec.hdi_work_location_id and rec.hdi_work_location_id.latitude and 
                rec.hdi_work_location_id.longitude):
                rec.check_in_distance = self._calculate_distance(
                    rec.check_in_latitude, rec.check_in_longitude,
                    rec.hdi_work_location_id.latitude, rec.hdi_work_location_id.longitude
                )
            
            # Calculate check-out distance
            if (rec.check_out_latitude and rec.check_out_longitude and 
                rec.hdi_checkout_location_id and rec.hdi_checkout_location_id.latitude and 
                rec.hdi_checkout_location_id.longitude):
                rec.check_out_distance = self._calculate_distance(
                    rec.check_out_latitude, rec.check_out_longitude,
                    rec.hdi_checkout_location_id.latitude, rec.hdi_checkout_location_id.longitude
                )

    def _calculate_distance(self, lat1, lon1, lat2, lon2):
        """Tính khoảng cách giữa 2 điểm GPS (Haversine formula)"""
        import math
        
        # Convert to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Earth radius in meters
        r = 6371000
        
        return r * c

    @api.depends('check_in', 'check_out', 'employee_id', 'hdi_work_shift')
    def _compute_attendance_status(self):
        """Tính trạng thái chấm công"""
        for rec in self:
            rec.hdi_is_late = False
            rec.hdi_is_early_leave = False
            rec.hdi_is_missing_checkout = False
            rec.hdi_late_minutes = 0.0
            rec.hdi_early_leave_minutes = 0.0
            
            if not rec.check_in:
                continue
                
            # Missing checkout
            if rec.check_in and not rec.check_out:
                rec.hdi_is_missing_checkout = True
                continue
                
            # Get work schedule
            resource_calendar = rec.employee_id.resource_calendar_id
            if not resource_calendar:
                continue
                
            # Check late/early based on shift
            if rec.hdi_work_shift == 'full':
                expected_start = 8.0  # 8:00 AM
                expected_end = 17.0   # 5:00 PM
            elif rec.hdi_work_shift == 'morning':
                expected_start = 6.0  # 6:00 AM
                expected_end = 14.0   # 2:00 PM
            elif rec.hdi_work_shift == 'afternoon':
                expected_start = 14.0 # 2:00 PM
                expected_end = 22.0   # 10:00 PM
            elif rec.hdi_work_shift == 'night':
                expected_start = 22.0 # 10:00 PM
                expected_end = 6.0    # 6:00 AM (next day)
            else:  # flexible
                continue
                
            # Grace period (phút)
            grace_period = 15  # 15 minutes grace
            
            # Check late
            if rec.check_in_time > (expected_start + grace_period/60.0):
                rec.hdi_is_late = True
                rec.hdi_late_minutes = (rec.check_in_time - expected_start) * 60
                
            # Check early leave
            if rec.check_out and rec.check_out_time < (expected_end - grace_period/60.0):
                rec.hdi_is_early_leave = True
                rec.hdi_early_leave_minutes = (expected_end - rec.check_out_time) * 60

    @api.depends('employee_id', 'check_in_date', 'hdi_work_shift')
    def _compute_expected_hours(self):
        """Tính số giờ làm việc quy định"""
        for rec in self:
            if not rec.employee_id or not rec.check_in_date:
                rec.hdi_expected_hours = 0.0
                continue
                
            resource_calendar = rec.employee_id.resource_calendar_id
            if not resource_calendar:
                rec.hdi_expected_hours = 8.0  # Default 8 hours
                continue
                
            # Calculate expected hours based on shift
            if rec.hdi_work_shift == 'full':
                rec.hdi_expected_hours = 8.0
            elif rec.hdi_work_shift in ['morning', 'afternoon', 'night']:
                rec.hdi_expected_hours = 8.0
            else:  # flexible
                rec.hdi_expected_hours = 8.0

    @api.depends('worked_hours', 'hdi_expected_hours')
    def _compute_overtime_hours(self):
        """Tính số giờ làm thêm"""
        for rec in self:
            if rec.worked_hours and rec.hdi_expected_hours:
                rec.hdi_overtime_hours = max(0, rec.worked_hours - rec.hdi_expected_hours)
            else:
                rec.hdi_overtime_hours = 0.0

    @api.depends('hdi_is_late', 'hdi_is_early_leave', 'hdi_is_missing_checkout', 'hdi_explanation_ids')
    def _compute_attendance_state(self):
        """Tính trạng thái tổng thể của chấm công"""
        for rec in self:
            if rec.hdi_explanation_ids:
                rec.hdi_attendance_state = 'explained'
            elif rec.hdi_is_missing_checkout:
                rec.hdi_attendance_state = 'missing_checkout'
            elif rec.hdi_is_late:
                rec.hdi_attendance_state = 'late'
            elif rec.hdi_is_early_leave:
                rec.hdi_attendance_state = 'early_leave'
            else:
                rec.hdi_attendance_state = 'normal'

    @api.depends('hdi_attendance_state', 'hdi_is_late', 'hdi_is_early_leave', 'hdi_is_missing_checkout')
    def _compute_color(self):
        """Tính màu cho calendar view"""
        for rec in self:
            if rec.hdi_attendance_state == 'explained':
                rec.color = 5  # Blue - explained
            elif rec.hdi_is_missing_checkout:
                rec.color = 1  # Red - missing checkout
            elif rec.hdi_is_late or rec.hdi_is_early_leave:
                rec.color = 3  # Orange - late/early
            else:
                rec.color = 10 # Green - normal

    @api.depends('hdi_explanation_ids')
    def _compute_explanation_count(self):
        """Đếm số lần giải trình"""
        for rec in self:
            rec.hdi_explanation_count = len(rec.hdi_explanation_ids)

    @api.depends('hdi_is_late', 'hdi_is_early_leave', 'hdi_is_missing_checkout', 'hdi_explanation_ids')
    def _compute_can_explain(self):
        """Kiểm tra có thể giải trình hay không"""
        for rec in self:
            has_issue = rec.hdi_is_late or rec.hdi_is_early_leave or rec.hdi_is_missing_checkout
            already_explained = bool(rec.hdi_explanation_ids)
            rec.hdi_can_explain = has_issue and not already_explained

    def action_explain_attendance(self):
        """Mở wizard giải trình chấm công"""
        self.ensure_one()
        return {
            'name': _('Giải trình chấm công'),
            'type': 'ir.actions.act_window',
            'res_model': 'attendance.explanation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_attendance_id': self.id,
                'default_employee_id': self.employee_id.id,
            }
        }

    def name_get(self):
        """Customize display name"""
        result = []
        for rec in self:
            name = f"{rec.employee_id.name} - {rec.check_in_date}"
            if rec.hdi_attendance_state != 'normal':
                name += f" ({dict(rec._fields['hdi_attendance_state'].selection)[rec.hdi_attendance_state]})"
            result.append((rec.id, name))
        return result

    @api.model
    def create(self, vals):
        """Override create to add tracking"""
        attendance = super().create(vals)
        if attendance.check_in:
            attendance.message_post(
                body=_("Check-in lúc %s") % attendance.check_in.strftime('%H:%M:%S')
            )
        return attendance

    def write(self, vals):
        """Override write to add tracking"""
        if 'check_out' in vals and vals['check_out']:
            for rec in self:
                if not rec.check_out:  # First time checkout
                    check_out_time = fields.Datetime.from_string(vals['check_out'])
                    rec.message_post(
                        body=_("Check-out lúc %s") % check_out_time.strftime('%H:%M:%S')
                    )
        return super().write(vals)

    @api.constrains('check_in', 'check_out')
    def _check_validity(self):
        """Validate attendance times"""
        for rec in self:
            if rec.check_in and rec.check_out and rec.check_out <= rec.check_in:
                raise ValidationError(_('Thời gian check-out phải sau thời gian check-in!'))

    @api.constrains('check_in_distance', 'check_out_distance')
    def _check_location_distance(self):
        """Validate location distance if configured"""
        for rec in self:
            settings = self.env['attendance.settings'].get_settings()
            if settings.enforce_location_checkin and rec.check_in_distance > settings.max_checkin_distance:
                raise ValidationError(
                    _('Vị trí check-in quá xa địa điểm làm việc! Khoảng cách: %.0f mét (Tối đa: %.0f mét)') %
                    (rec.check_in_distance, settings.max_checkin_distance)
                )
            if settings.enforce_location_checkout and rec.check_out_distance > settings.max_checkout_distance:
                raise ValidationError(
                    _('Vị trí check-out quá xa địa điểm làm việc! Khoảng cách: %.0f mét (Tối đa: %.0f mét)') %
                    (rec.check_out_distance, settings.max_checkout_distance)
                )