# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, time, timedelta
from pytz import timezone, UTC
from math import sin, cos, sqrt, atan2, radians
import logging

_logger = logging.getLogger(__name__)


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    note = fields.Text(string='Ghi chú')
    date = fields.Date(string='Ngày', compute='_compute_date_and_day', store=True)
    en_dayofweek = fields.Char(string='Thứ', compute='_compute_date_and_day', store=True)

    # Location fields
    en_location_id = fields.Many2one(
        'hr.work.location',
        string='Địa điểm check in',
        compute='_compute_en_location_id',
        store=True,
        readonly=False
    )
    en_location_checkout_id = fields.Many2one(
        'hr.work.location',
        string='Địa điểm check out',
        compute='_compute_en_location_checkout_id',
        store=True,
        readonly=False
    )
    en_checkin_distance = fields.Float(
        string='Khoảng cách check in (km)',
        compute='_compute_en_checkin_distance',
        store=True
    )
    en_checkout_distance = fields.Float(
        string='Khoảng cách check out (km)',
        compute='_compute_en_checkout_distance',
        store=True
    )

    # Status fields
    en_missing_attendance = fields.Boolean(string='Quên chấm công', default=False, copy=False)
    en_late = fields.Boolean(string='Đi muộn', compute='_get_en_late', store=True, copy=False)
    en_soon = fields.Boolean(string='Về sớm', compute='_get_en_soon', store=True, copy=False)

    color = fields.Integer(string='Màu', compute='_compute_color', store=False)
    warning_message = fields.Text(string='Thông báo', compute='_compute_color', store=False)

    check_in_date = fields.Date(string='Ngày checkin', compute='_compute_check_in_date', store=True)
    check_in_time = fields.Float(string='Giờ checkin', compute='_compute_check_in_date', store=True)
    check_out_date = fields.Date(string='Ngày checkout', compute='_compute_check_out_date', store=True)
    check_out_time = fields.Float(string='Giờ checkout', compute='_compute_check_out_date', store=True)

    explanation_required = fields.Boolean(string='Cần giải trình', compute='_compute_explanation_required', store=True)
    explanation_id = fields.Many2one('hr.attendance.explanation', string='Giải trình', readonly=True)
    explanation_month_count = fields.Integer(
        string='Số lần đã giải trình trong tháng',
        compute='_compute_explanation_month_count'
    )

    employee_barcode = fields.Char(string='Mã nhân viên', related='employee_id.barcode', store=True)

    @api.depends('check_in', 'employee_id')
    def _compute_date_and_day(self):
        """Compute date and day of week from check_in"""
        for rec in self:
            if rec.check_in and rec.employee_id:
                tz = rec.employee_id.tz or 'UTC'
                check_in_tz = rec.check_in.replace(tzinfo=UTC).astimezone(timezone(tz))
                rec.date = check_in_tz.date()
                weekdays = ['Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'Chủ nhật']
                rec.en_dayofweek = weekdays[check_in_tz.weekday()]
            else:
                rec.date = False
                rec.en_dayofweek = False

    @api.depends('employee_id')
    def _compute_en_location_id(self):
        """Set default location from employee"""
        for rec in self:
            if not rec.en_location_id and rec.employee_id:
                rec.en_location_id = rec.employee_id.work_location_id

    @api.depends('en_location_id')
    def _compute_en_location_checkout_id(self):
        """Set checkout location same as checkin by default"""
        for rec in self:
            if rec.en_location_id and not rec.en_location_checkout_id:
                rec.en_location_checkout_id = rec.en_location_id

    @api.depends('check_in', 'check_in_latitude', 'check_in_longitude', 'en_location_id')
    def _compute_en_checkin_distance(self):
        """Calculate distance from check-in location"""
        for rec in self:
            if rec.check_in_latitude and rec.check_in_longitude and rec.en_location_id:
                rec.en_checkin_distance = self.en_distance(
                    rec.check_in_latitude,
                    rec.check_in_longitude,
                    rec.en_location_id.latitude,
                    rec.en_location_id.longitude
                )
            else:
                rec.en_checkin_distance = 0.0

    @api.depends('check_out', 'check_out_latitude', 'check_out_longitude', 'en_location_checkout_id')
    def _compute_en_checkout_distance(self):
        """Calculate distance from check-out location"""
        for rec in self:
            if rec.check_out_latitude and rec.check_out_longitude and rec.en_location_checkout_id:
                rec.en_checkout_distance = self.en_distance(
                    rec.check_out_latitude,
                    rec.check_out_longitude,
                    rec.en_location_checkout_id.latitude,
                    rec.en_location_checkout_id.longitude
                )
            else:
                rec.en_checkout_distance = 0.0

    @api.depends('check_in')
    def _compute_check_in_date(self):
        """Split check_in into date and time"""
        for rec in self:
            if rec.check_in and rec.employee_id:
                tz = rec.employee_id.tz or 'UTC'
                check_in_tz = rec.check_in.replace(tzinfo=UTC).astimezone(timezone(tz))
                rec.check_in_date = check_in_tz.date()
                rec.check_in_time = check_in_tz.hour + check_in_tz.minute / 60.0
            else:
                rec.check_in_date = False
                rec.check_in_time = 0.0

    @api.depends('check_out')
    def _compute_check_out_date(self):
        """Split check_out into date and time"""
        for rec in self:
            if rec.check_out and rec.employee_id:
                tz = rec.employee_id.tz or 'UTC'
                check_out_tz = rec.check_out.replace(tzinfo=UTC).astimezone(timezone(tz))
                rec.check_out_date = check_out_tz.date()
                rec.check_out_time = check_out_tz.hour + check_out_tz.minute / 60.0
            else:
                rec.check_out_date = False
                rec.check_out_time = 0.0

    @api.depends('check_in', 'employee_id')
    def _get_en_late(self):
        """Check if employee is late"""
        for rec in self:
            rec.en_late = False
            if not rec.check_in or not rec.employee_id or rec.en_missing_attendance:
                continue

            calendar = rec.employee_id.resource_calendar_id
            if not calendar:
                continue

            tz = rec.employee_id.tz or 'UTC'
            check_in_tz = rec.check_in.replace(tzinfo=UTC).astimezone(timezone(tz))

            # Get work schedule for the day
            day_of_week = str(check_in_tz.weekday())
            attendances = calendar.attendance_ids.filtered(
                lambda a: a.dayofweek == day_of_week and a.day_period == 'morning'
            )

            if attendances:
                # Get expected check-in time
                expected_hour = attendances[0].hour_from
                actual_hour = check_in_tz.hour + check_in_tz.minute / 60.0

                # Late if more than 15 minutes after expected time
                if actual_hour > (expected_hour + 0.25):  # 0.25 = 15 minutes
                    rec.en_late = True

    @api.depends('check_out', 'employee_id')
    def _get_en_soon(self):
        """Check if employee left early"""
        for rec in self:
            rec.en_soon = False
            if not rec.check_out or not rec.employee_id or rec.en_missing_attendance:
                continue

            calendar = rec.employee_id.resource_calendar_id
            if not calendar:
                continue

            tz = rec.employee_id.tz or 'UTC'
            check_out_tz = rec.check_out.replace(tzinfo=UTC).astimezone(timezone(tz))

            # Get work schedule for the day
            day_of_week = str(check_out_tz.weekday())
            attendances = calendar.attendance_ids.filtered(
                lambda a: a.dayofweek == day_of_week and a.day_period == 'afternoon'
            )

            if attendances:
                # Get expected check-out time
                expected_hour = attendances[0].hour_to
                actual_hour = check_out_tz.hour + check_out_tz.minute / 60.0

                # Early if more than 15 minutes before expected time
                if actual_hour < (expected_hour - 0.25):  # 0.25 = 15 minutes
                    rec.en_soon = True

    @api.depends('en_missing_attendance', 'en_late', 'en_soon', 'date', 'employee_id', 'check_out')
    def _compute_color(self):
        """Compute color for calendar view"""
        for rec in self:
            color = 10  # Default: green
            warning_message = []

            if rec.en_missing_attendance:
                color = 2  # Red - missing attendance
                warning_message.append('Quên chấm công')
            elif not rec.check_out:
                color = 3  # Yellow - not checked out yet
                warning_message.append('Chưa checkout')
            else:
                # Check if timesheet exists and is approved
                if rec.date and rec.employee_id:
                    # This would need integration with timesheet module
                    # For now, just basic checks
                    pass

                if rec.en_late:
                    warning_message.append('Đi muộn')
                    color = 1  # Orange

                if rec.en_soon:
                    warning_message.append('Về sớm')
                    color = 1  # Orange

                if rec.worked_hours < 7.75 and not warning_message:
                    warning_message.append('Thiếu giờ')
                    color = 4

            rec.color = color
            rec.warning_message = '\n'.join(warning_message) if warning_message else ''

    def _compute_explanation_month_count(self):
        """Count explanations in current month"""
        for rec in self:
            if rec.date and rec.employee_id:
                month_start = rec.date.replace(day=1)
                month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)

                count = self.env['hr.attendance.explanation'].search_count([
                    ('employee_id', '=', rec.employee_id.id),
                    ('explanation_date', '>=', month_start),
                    ('explanation_date', '<=', month_end),
                    ('state', '!=', 'refused')
                ])
                rec.explanation_month_count = count
            else:
                rec.explanation_month_count = 0

    @api.depends('check_in', 'check_out', 'employee_id')
    def _compute_explanation_required(self):
        """Check if attendance requires explanation"""
        for attendance in self:
            attendance.explanation_required = bool(
                attendance.en_missing_attendance or
                attendance.en_late or
                attendance.en_soon
            )

    def button_create_explanation(self):
        """Open wizard to create attendance explanation"""
        self.ensure_one()
        return {
            'name': _('Giải trình chấm công'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.attendance.explanation',
            'view_mode': 'form',
            'context': {
                'default_attendance_id': self.id,
                'default_employee_id': self.employee_id.id,
                'default_date': self.check_in.date() if self.check_in else fields.Date.today(),
            },
            'target': 'new',
        }

    def button_create_hr_leave(self):
        """Open wizard to create leave request"""
        self.ensure_one()
        return {
            'name': _('Xin nghỉ phép'),
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

    def en_distance(self, from_lat, from_long, to_lat, to_long):
        """Calculate distance between two GPS coordinates using Haversine formula"""
        if not all([from_lat, from_long, to_lat, to_long]):
            return 0.0

        # Radius of Earth in kilometers
        R = 6373.0

        lat1 = radians(from_lat)
        lon1 = radians(from_long)
        lat2 = radians(to_lat)
        lon2 = radians(to_long)

        dlon = lon2 - lon1
        dlat = lat2 - lat1

        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        distance = R * c
        return round(distance, 2)

    @api.model
    def auto_log_out_job(self):
        """Cron job: Auto checkout at 23:59 for missing checkout"""
        today = fields.Date.today()
        yesterday = today - timedelta(days=1)

        # Find attendances without checkout
        attendances = self.search([
            ('check_in', '>=', yesterday),
            ('check_in', '<', today),
            ('check_out', '=', False),
        ])

        for attendance in attendances:
            try:
                # Set checkout to 23:59 of check-in day
                tz = attendance.employee_id.tz or 'UTC'
                check_in_date = attendance.check_in.replace(tzinfo=UTC).astimezone(timezone(tz)).date()
                checkout_time = datetime.combine(check_in_date, time(23, 59, 0))
                checkout_time_utc = timezone(tz).localize(checkout_time).astimezone(UTC).replace(tzinfo=None)

                attendance.write({
                    'check_out': checkout_time_utc,
                })
                _logger.info(f'Auto checkout for employee {attendance.employee_id.name}')
            except Exception as e:
                _logger.error(f'Error auto checkout for {attendance.employee_id.name}: {e}')

    def name_get(self):
        """Custom name_get to show employee name and date"""
        result = []
        for attendance in self:
            if attendance.check_in:
                name = f"{attendance.employee_id.name} - {attendance.date}"
                result.append((attendance.id, name))
            else:
                result.append((attendance.id, attendance.employee_id.name))
        return result

    @api.model
    def _attendance_action_change(self):
        """Override to add async logging - prevent double click"""
        result = super()._attendance_action_change()

        # Log the action
        if result:
            self.env['hr.attendance.log'].create({
                'attendance_id': result.get('attendance', {}).get('id'),
                'employee_id': self.env.user.employee_id.id,
                'action_time': fields.Datetime.now(),
                'action_type': result.get('action'),
            })

        return result

