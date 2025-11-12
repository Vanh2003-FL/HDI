from odoo import fields, models, api, Command
import logging
from odoo.tools import float_round
from dateutil.relativedelta import relativedelta
from pytz import timezone, UTC
from datetime import datetime, timedelta, time
from geopy.geocoders import Nominatim

_logger = logging.getLogger(__name__)
import pytz

from math import sin, cos, sqrt, atan2, radians, modf


class HrAttendance(models.Model):
    _name = 'hr.attendance'
    _inherit = ['hr.attendance', 'mail.thread', 'mail.activity.mixin']

    en_location_checkout_id = fields.Many2one(string='Địa điểm check out', comodel_name='hr.work.location', compute='_compute_en_location_checkout_id', store=True, readonly=True)
    en_area_id = fields.Many2one(related='employee_id.en_area_id')

    @api.depends('en_location_id')
    def _compute_en_location_checkout_id(self):
        for rec in self:
            rec.en_location_checkout_id = rec.en_location_id

    # @api.depends('check_in_longitude', 'check_in_latitude')
    # def _compute_based_on_checkin(self):
    #     geolocator = Nominatim(user_agent='my-app')
    #     for rec in self:
    #         if not rec.check_in_longitude and not rec.check_in_latitude:
    #             rec.check_in_address = False
    #             rec.check_in_address_url = False
    #             continue
    #         try:
    #             location = geolocator.reverse(str(rec.check_in_latitude) + ', ' + str(rec.check_in_longitude))
    #             rec.check_in_address = location.address
    #             rec.check_in_address_url = 'https://www.google.com/maps/place/' + location.address
    #         except Exception as e:
    #             _logger.info(str(e))
    #             rec.check_in_address = False
    #             rec.check_in_address_url = False
    #
    # @api.depends('check_out_longitude', 'check_out_latitude')
    # def _compute_based_on_checkout(self):
    #     geolocator = Nominatim(user_agent='my-app')
    #     for rec in self:
    #         if not rec.check_out_longitude and not rec.check_out_latitude:
    #             rec.check_out_address = False
    #             rec.check_out_address_url = False
    #             continue
    #         try:
    #             location = geolocator.reverse(str(rec.check_out_latitude) + ', ' + str(rec.check_out_longitude))
    #             rec.check_out_address = location.address
    #             rec.check_out_address_url = 'https://www.google.com/maps/place/' + location.address
    #         except Exception as e:
    #             _logger.info(str(e))
    #             rec.check_out_address = False
    #             rec.check_out_address_url = False

    date = fields.Date(store=True, string='Ngày', compute='_compute_en_dayofweek')

    @api.depends('check_in', 'employee_id', 'employee_id.tz')
    def _compute_en_dayofweek(self):
        for rec in self:
            if not rec.check_in:
                rec.en_dayofweek = False
                rec.date = False
                continue
            rec.date = rec.check_in.replace(tzinfo=UTC).astimezone(timezone(rec.employee_id.tz or self.env.user.tz or 'Asia/Ho_Chi_Minh')).date()
            rec.en_dayofweek = str(rec.date.weekday())

    en_dayofweek = fields.Selection(store=True, string='Ngày trong tuần', compute='_compute_en_dayofweek', selection=[('0', 'Thứ 2'), ('1', 'Thứ 3'), ('2', 'Thứ 4'), ('3', 'Thứ 5'), ('4', 'Thứ 6'), ('5', 'Thứ 7'), ('6', 'Chủ nhật'), ])

    def _update_overtime(self, employee_attendance_dates=None):
        return

    en_checkin_distance = fields.Float(string='Khoảng cách checkin', digits="Location", compute='_compute_en_checkin_distance', store=True)

    @api.depends('en_location_id', 'check_in_longitude', 'check_in_latitude', 'check_in')
    def _compute_en_checkin_distance(self):
        for rec in self:
            en_checkin_distance = 0
            if not rec.en_location_id or (not rec.en_location_id.en_latitude and not rec.en_location_id.en_longitude) or (not rec.check_in_longitude and not rec.check_in_latitude):
                rec.en_checkin_distance = en_checkin_distance
                continue
            rec.en_checkin_distance = self.en_distance(rec.check_in_latitude, rec.check_in_longitude, rec.en_location_id.en_latitude, rec.en_location_id.en_longitude)

    en_checkout_distance = fields.Float(string='Khoảng cách checkout', digits="Location", compute='_compute_en_checkout_distance', store=True)

    @api.depends('en_location_checkout_id', 'check_out_longitude', 'check_out_latitude')
    def _compute_en_checkout_distance(self):
        for rec in self:
            en_checkout_distance = 0
            if not rec.en_location_checkout_id or (not rec.en_location_checkout_id.en_latitude and not rec.en_location_checkout_id.en_longitude) or (not rec.check_out_longitude and not rec.check_out_latitude):
                rec.en_checkout_distance = en_checkout_distance
                continue
            rec.en_checkout_distance = self.en_distance(rec.check_out_latitude, rec.check_out_longitude, rec.en_location_checkout_id.en_latitude, rec.en_location_checkout_id.en_longitude)

    en_location_id = fields.Many2one(string='Địa điểm làm việc', comodel_name='hr.work.location', compute='_compute_en_location_id', store=True, readonly=False)

    @api.depends('employee_id')
    def _compute_en_location_id(self):
        for rec in self:
            en_location_id = rec.en_location_id
            if rec.employee_id and en_location_id != rec.employee_id.work_location_id:
                en_location_id = rec.employee_id.work_location_id
            if not en_location_id:
                en_location_id = rec.employee_id.work_location_id
            if not en_location_id:
                en_location_id = self.env['hr.work.location'].search([], order='id asc', limit=1)
            rec.en_location_id = en_location_id

    en_missing_attendance = fields.Boolean(string='Quên chấm công', default=False, copy=False)

    en_late = fields.Boolean(string='Đi muộn', compute='_get_en_late', copy=False, store=True)
    en_soon = fields.Boolean(string='Về sớm', compute='_get_en_soon', copy=False, store=True)
    employee_barcode = fields.Char(string='Mã nhân viên', related='employee_id.barcode', store=True)

    @api.depends('check_in', 'employee_id')
    def _get_en_late(self):
        en_late_request = float(self.env['ir.config_parameter'].sudo().get_param('en_late_request'))
        for attendance in self:
            en_late = False
            if attendance.check_in:
                calendar_id = attendance.employee_id.resource_calendar_id
                tz = timezone(calendar_id.tz or self.env.user.tz or 'UTC')
                check_time = attendance.check_in + attendance.check_in.astimezone(tz).utcoffset()
                check_time = tz.localize(check_time)
                dfrom = datetime.combine(check_time.date(), time.min).replace(tzinfo=pytz.UTC)
                dto = datetime.combine(check_time.date(), time.max).replace(tzinfo=pytz.UTC)
                intervals = calendar_id._work_intervals_batch(dfrom, dto, attendance.employee_id.resource_id)[attendance.employee_id.resource_id.id]
                for start, stop, meta in intervals:
                    if en_late_request > 0:
                        start += timedelta(hours=en_late_request)
                    en_late = start < check_time
                    break
            attendance.en_late = en_late

    @api.depends('check_out', 'employee_id')
    def _get_en_soon(self):
        en_soon_request = float(self.env['ir.config_parameter'].sudo().get_param('en_soon_request'))
        for attendance in self:
            en_soon = False
            if attendance.check_out:
                calendar_id = attendance.employee_id.resource_calendar_id
                tz = timezone(calendar_id.tz or self.env.user.tz or 'UTC')
                check_time = attendance.check_out + attendance.check_out.astimezone(tz).utcoffset()
                check_time = tz.localize(check_time)
                dfrom = datetime.combine(check_time.date(), time.min).replace(tzinfo=pytz.UTC)
                dto = datetime.combine(check_time.date(), time.max).replace(tzinfo=pytz.UTC)
                intervals = calendar_id._work_intervals_batch(dfrom, dto, attendance.employee_id.resource_id)[attendance.employee_id.resource_id.id]
                stop_time = False
                for start, stop, meta in intervals:
                    stop_time = stop
                if stop_time and en_soon_request > 0:
                    stop_time -= timedelta(hours=en_soon_request)
                en_soon = stop_time and check_time < stop_time
            attendance.en_soon = en_soon

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        res.notify_soon_late()
        return res

    def write(self, values):
        res = super().write(values)
        if 'check_in' in values or 'check_out' in values or 'employee_id' in values:
            self.notify_soon_late()
        return res

    def notify_soon_late(self):
        return
        en_max_attendance_request = float(self.env['ir.config_parameter'].sudo().get_param('en_max_attendance_request'))
        for rec in self:
            if rec.en_soon:
                rec.send_notify(
                    f'''
                    Bạn có bản ghi Về sớm cần giải trình. Vui lòng giải trình trong khoảng thời gian {en_max_attendance_request} giờ
                    Nếu không thực hiện giải trình trong khoảng thời gian này, người dùng sẽ không được phép giải trình bản ghi này nữa.
                    ''', rec.employee_id.user_id, 'Về sớm'
                )
            if rec.en_late:
                rec.send_notify(
                    f'''
                    Bạn có bản ghi Đi muộn cần giải trình. Vui lòng giải trình trong khoảng thời gian {en_max_attendance_request} giờ
                    Nếu không thực hiện giải trình trong khoảng thời gian này, người dùng sẽ không được phép giải trình bản ghi này nữa.
                    ''', rec.employee_id.user_id, 'Đi muộn'
                )

    @api.depends('check_in', 'check_out', 'employee_id', 'en_missing_attendance')
    def _compute_worked_hours(self):
        for attendance in self:
            resource = attendance.employee_id.resource_calendar_id
            if attendance.en_missing_attendance:
                attendance.worked_hours = False
            else:
                if attendance.check_out and attendance.check_in:
                    if not resource or resource.attendance_type == 'actual':
                        delta = attendance.check_out - attendance.check_in
                        attendance.worked_hours = float_round(delta.total_seconds() / 60 / (resource.round or 1), 0) * (resource.round or 1) / 60
                    elif resource.attendance_type == 'fixed':
                        tz = attendance.employee_id.tz
                        worked_hours = attendance.employee_id._get_work_days_data_batch(timezone(tz).localize(attendance.check_in + relativedelta(hour=0, minute=0, second=0)).astimezone(UTC).replace(tzinfo=None), timezone(tz).localize(attendance.check_out + relativedelta(hour=23, minute=59, second=59)).astimezone(UTC).replace(tzinfo=None), calendar=resource).get(attendance.employee_id.id, {}).get('hours')
                        attendance.worked_hours = float_round(worked_hours * 3600 / 60 / (resource.round or 1), 0) * (resource.round or 1) / 60
                    elif resource.attendance_type == 'not_ot':
                        worked_hours = attendance.employee_id._get_work_days_data_batch(attendance.check_in, attendance.check_out, calendar=resource).get(attendance.employee_id.id, {}).get('hours')
                        attendance.worked_hours = float_round(worked_hours * 3600 / 60 / (resource.round or 1), 0) * (resource.round or 1) / 60
                else:
                    attendance.worked_hours = False

    def auto_log_out_job(self):
        en_max_attendance_request = float(self.env['ir.config_parameter'].sudo().get_param('en_max_attendance_request'))
        records = self.search([('check_out', '=', False), ('employee_id.resource_calendar_id.en_auto_checkout', '=', True)])
        for rec in records:
            tz = rec.employee_id.tz or self.env.user.tz or 'Asia/Ho_Chi_Minh'
            tz_check_out = rec.check_in.astimezone(timezone(tz)).date()
            check_out = timezone(tz).localize(datetime.combine(tz_check_out, time.max)).astimezone(timezone('UTC')).replace(tzinfo=None)
            rec.write(dict(en_missing_attendance=True, check_out=check_out, worked_hours=0))
            rec._compute_worked_hours()
            if en_max_attendance_request >= 0:
                rec.send_notify(
                    f'Bạn có bản ghi quên chấm công cần giải trình. Vui lòng giải trình trong khoảng {en_max_attendance_request} giờ. Nếu không thực hiện giải trình trong khoảng thời gian này, người dùng sẽ không được phép giải trình bản ghi này nữa.',
                    rec.employee_id.user_id,
                    'Giải trình chấm công'
                )
            else:
                rec.send_notify(
                    f'Bạn có bản ghi quên chấm công cần giải trình.',
                    rec.employee_id.user_id,
                    'Giải trình chấm công'
                )

    def en_distance(self, from_lat, from_long, to_lat, to_long):
        R = 6373.0

        lat1 = radians(from_lat)
        lon1 = radians(from_long)
        lat2 = radians(to_lat)
        lon2 = radians(to_long)

        dlon = lon2 - lon1
        dlat = lat2 - lat1

        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        return R * c

    explanation_month_count = fields.Integer(string='Số lần đã giải trình trong tháng', compute='_compute_explanation_month_count')

    def _compute_explanation_month_count(self):
        en_attendance_request_start = int(
            self.env['ir.config_parameter'].sudo().get_param('en_attendance_request_start'))
        for rec in self:
            if en_attendance_request_start:
                try:
                    date_from = rec.date + relativedelta(day=en_attendance_request_start, months=-1)
                    date_to = rec.date + relativedelta(day=en_attendance_request_start, days=-1)
                except:
                    date_from = rec.date + relativedelta(day=1)
                    date_to = rec.date + relativedelta(day=1, months=1, days=-1)
            else:
                date_from = rec.date + relativedelta(day=1)
                date_to = rec.date + relativedelta(day=1, months=1, days=-1)
            _domain = [('employee_id', '=', rec.employee_id.id),
                       ('state', 'in', ['to_approve', 'approved']),
                       ('explanation_date', '>=', date_from),
                       ('explanation_date', '<=', date_to)]
            records = self.env['hr.attendance.explanation'].search(_domain)
            rec.explanation_month_count = len(set(records.mapped('explanation_date')))

    def button_create_explanation(self):
        action = self.env["ir.actions.actions"]._for_xml_id("ngs_attendance.hr_attendance_explanation_my_action")
        action['context'] = {
            'default_employee_id': self.employee_id.id,
            'default_hr_attendance_id': self.id
        }
        action['views'] = [(False, 'form')]
        action['view_mode'] = 'form'
        return action

    def button_create_hr_leave(self):
        action = self.env["ir.actions.actions"]._for_xml_id("hr_holidays.hr_leave_action_my")
        action['views'] = [(False, 'form')]
        action['view_mode'] = 'form'
        return action

    color = fields.Integer(string="Màu", compute='_compute_color', store=False)
    warning_message = fields.Text(string='Thông báo', compute='_compute_color')

    @api.depends('en_missing_attendance', 'en_late', 'en_soon', 'date', 'employee_id')
    def _compute_color(self):
        check_hour = float(self.env['ir.config_parameter'].sudo().get_param('check_timesheet_before_checkout_hour'))
        for rec in self:
            warning_message = []
            igone_soon_late = rec.employee_id.resource_calendar_id.attendance_type == 'actual' and rec.worked_hours > check_hour
            if rec.en_missing_attendance:
                warning_message.append('Quên check-out')
            if rec.en_late and not igone_soon_late:
                warning_message.append('Đi muộn')
            if rec.en_soon and not igone_soon_late:
                warning_message.append('Về sớm')
            if rec.employee_id.check_timesheet_before_checkout:
                if not self.env['account.analytic.line'].search_count([('employee_id', '=', rec.employee_id.id), ('date', '=', rec.date)]) and not self.env['hr.leave'].search_count([('employee_id', '=', rec.employee_id.id), ('request_date_from', '<=', rec.date), ('request_date_to', '>=', rec.date)]):
                    warning_message.append('Chưa khai Timesheet')
                else:
                    timesheet_hour = rec.employee_id.get_hour_working_by_day(rec.date)
                    if -1 < timesheet_hour < check_hour:
                        warning_message.append('Timesheet chưa được duyệt')
            if warning_message:
                color = 1
            else:
                color = 10
                if rec.worked_hours < 7.75:
                    hours_total = rec._get_number_of_hours_leave()
                    worked_hours = rec.worked_hours + hours_total
                    if worked_hours < 7.75:
                        color = 1
                        warning_message.append('Không đủ số giờ công trong ngày')
            rec.color = color
            rec.warning_message = '\n'.join(warning_message)

    def _get_number_of_hours_leave(self):
        domain = [
            ('employee_id', '=', self.employee_id.id),
            ('request_date_from', '<=', self.date),
            ('request_date_to', '>=', self.date),
            ('state', '=', 'validate')
        ]
        leaves = self.env['hr.leave'].sudo().search(domain)
        hours_total = 0.0
        for leave in leaves:
            if leave.request_date_from == leave.request_date_to:
                hours_total += leave.number_of_hours_display
            else:
                # Cộng 8 giờ vì là request nghỉ dài ngày
                hours_total += 8
        return hours_total

    def name_get(self):
        return super(HrAttendance, self.sudo()).name_get()

    check_in_date = fields.Date(string='Ngày checkin', compute='_compute_check_in_date', store=True)
    check_in_time = fields.Float(string='Giờ checkin', compute='_compute_check_in_date', store=True, float_time=True)
    check_out_date = fields.Date(string='Ngày checkout', compute='_compute_check_out_date', store=True)
    check_out_time = fields.Float(string='Giờ checkout', compute='_compute_check_out_date', store=True, float_time=True)

    @api.depends('check_in')
    def _compute_check_in_date(self):
        for rec in self:
            if rec.check_in:
                check_in = rec.check_in.replace(tzinfo=UTC).astimezone(timezone(rec.employee_id.tz or self.env.user.tz or 'Asia/Ho_Chi_Minh'))
                rec.check_in_date = check_in.date()
                rec.check_in_time = check_in.hour + rec.check_in.minute / 60
            else:
                rec.check_in_date = False
                rec.check_in_time = False

    @api.depends('check_out')
    def _compute_check_out_date(self):
        for rec in self:
            if rec.check_out:
                check_out = rec.check_out.replace(tzinfo=UTC).astimezone(timezone(rec.employee_id.tz or self.env.user.tz or 'Asia/Ho_Chi_Minh'))
                rec.check_out_date = check_out.date()
                rec.check_out_time = check_out.hour + rec.check_out.minute / 60
            else:
                rec.check_out_date = False
                rec.check_out_time = False
