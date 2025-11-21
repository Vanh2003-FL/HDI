from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _, exceptions
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)
from odoo.addons.ngsd_base.model.hr_employee import daterange


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    en_checked_diff_ok = fields.Char(string='Checkout khác địa điểm', compute='_compute_en_checked_diff_ok', groups='hr.group_hr_user')

    def attendance_manual(self, next_action, entered_pin=None):
        if self.shift == 'ca_vip':
            return {'warning': 'Ca làm việc của bạn thuộc ca VIP - không cần chấm công. Vui lòng liên hệ quản trị viên để được hỗ trợ'}
        latitude = self._context.get('latitude', False)
        longitude = self._context.get('longitude', False)
        _logger.info('attendance_manual_log: %s - %s - %s - %s', self.name, self.id, latitude, longitude)
        # if self.attendance_state == 'checked_in' and self.check_timesheet_before_checkout:
        #         #     timesheet_hour = self.get_hour_working_by_day(fields.Date.Date.Date.context_today(self))
        #         #     check_hour = float(self.env['ir.config_parameter'].sudo().get_param('check_timesheet_before_checkout_hour'))
        #         #     if -1 < timesheet_hour < check_hour:
        #         #         raise UserError('Thời gian log timesheet hôm nay của bạn là: %s giờ, bạn cần log timesheet đủ %s giờ. Vui lòng kiểm tra lại.'%(timesheet_hour, check_hour))
        # return {'warning': 'Thời gian log timesheet hôm nay của bạn là: %s giờ, bạn cần log timesheet đủ %s giờ. Vui lòng kiểm tra lại.'%(timesheet_hour, check_hour)}
        return super().attendance_manual(next_action, entered_pin)

    def cron_noti_missing_timesheet(self):
        today = fields.Date.Date.Date.context_today(self)
        start_period = 25
        history = self.env['ir.config_parameter'].sudo().get_param('cron_noti_missing_timesheet', False)
        history = history and fields.Date.from_string(history)
        self.env['ir.config_parameter'].sudo().set_param('cron_noti_missing_timesheet', today)
        if history and today > history and today.weekday() == 4 or today.day == (start_period - 1):
            day = today.day
            start_date = today + relativedelta(day=start_period)
            if day < start_period:
                start_date -= relativedelta(months=1)
            check_hour = float(self.env['ir.config_parameter'].sudo().get_param('check_timesheet_before_checkout_hour'))
            employees = self.search([('check_timesheet_before_checkout', '=', True)])
            for employee in employees:
                missing_ts = []
                for date_r in daterange(start_date, today):
                    timesheet_hour = employee.get_hour_working_by_day(date_r)
                    if -1 < timesheet_hour < check_hour:
                        missing_ts.append(f'    - {date_r.strftime("%d/%m/%Y")}')
                if missing_ts:
                    employee.send_notify_missing_ts(employee.user_id, missing_ts)

    def cron_noti_missing_approve_timesheet(self):
        today = fields.Date.Date.Date.context_today(self)
        start_period = 25
        history = self.env['ir.config_parameter'].sudo().get_param('cron_noti_missing_approve_timesheet', False)
        history = history and fields.Date.from_string(history)
        self.env['ir.config_parameter'].sudo().set_param('cron_noti_missing_approve_timesheet', today)
        if history and today > history and today.weekday() == 4 or today.day == (start_period - 1):
            day = today.day
            start_date = today + relativedelta(day=start_period)
            if day < start_period:
                start_date -= relativedelta(months=1)
            no_approved = self.env['account.analytic.line'].search([('date', '>=', start_date), ('date', '<=', today), ('en_state', '=', 'sent')])
            if no_approved:
                message = 'Dear anh/chị, hiện tại anh/chị đang có bản ghi Timesheet được gửi đến nhưng chưa được duyệt. Anh/chị vui lòng kiểm tra lại và duyệt các bản ghi Timesheet đó trước ...h ngày...'
                action = self.env.ref('hr_timesheet.timesheet_action_all')
                access_link = f'#action={action.id}&model=account.analytic.line&view_type=list'
                no_approved[0].send_notify(message, no_approved.en_approver_id, subject='Cảnh báo chưa duyệt Timesheet', model_description='Timesheet', access_link=access_link)

    def send_notify_missing_ts(self, users, data_days=None):
        self.clear_caches()
        view = self.env['ir.ui.view'].browse(self.env['ir.model.data']._xmlid_to_res_id('ngs_attendance.notify_missing_ts_record_message'))
        for record in self.sudo():
            if not record.exists():
                continue
            record.message_subscribe(partner_ids=users.mapped('partner_id').ids)
            model_description = self.env['ir.model']._get(record._name).display_name
            values = {
                'object': record,
                'model_description': model_description,
                'data_days': data_days or [],
                'access_link': record._notify_get_action_link('view'),
            }
            assignation_msg = view._render(values, engine='ir.qweb', minimal_qcontext=True)
            assignation_msg = record.env['mail.render.mixin']._replace_local_links(assignation_msg)
            record.message_notify(
                subject='Cảnh báo Timesheet chưa đủ điều kiện',
                body=assignation_msg,
                partner_ids=users.mapped('partner_id').ids,
                record_name=record.display_name,
                email_layout_xmlid='mail.mail_notification_light',
                model_description=model_description,
            )

    def get_en_checked_diff_ok(self):
        return (self.user_id or self.env.user).has_group('ngs_attendance.group_en_checkout_location')

    def _attendance_action(self, next_action):
        res = super()._attendance_action(next_action)
        action_message = res.get('action')
        action_message['total_overtime'] = 0
        action_message['overtime_today'] = 0
        action_message['hours_today'] = 0
        return {'action': action_message}

    def get_working_locations(self):
        default_location = self.work_location_id or self.env['hr.work.location'].search([], order='id asc', limit=1)
        if self.last_attendance_id and not self.last_attendance_id.check_out:
            default_location = self.last_attendance_id.en_location_id
        res = []
        if self.shift == 'ca_linh_hoat':
            res.append({'id': 0, 'name': 'Địa điểm khác', 'default_value': 0})
        res += [{'id': location.id, 'name': location.name, 'default_value': default_location.id} for location in self.env['hr.work.location'].search([])]
        return res

    def _attendance_action_change(self):
        res = super(HrEmployee, self.sudo())._attendance_action_change()
        en_max_distance = float(self.env['ir.config_parameter'].sudo().get_param('en_max_distance'))
        en_location_id = int(self.env.context.get("en_location_id", False)) or False
        if en_location_id:
            location = self.env['hr.work.location'].browse(en_location_id)
            if not location.en_latitude and not location.en_longitude:
                raise UserError("Địa điểm làm việc chưa được xác nhận vị trí, vui lòng liên hệ với người quản trị!")
        if self.attendance_state == 'checked_in':
            if en_location_id and en_max_distance > 0:
                if not res.check_in_latitude and not res.check_in_longitude:
                    raise UserError("Bạn chưa cung cấp quyền truy cập vị trí, không thể check in")
                # if not en_location_id:
                #     raise UserError("Khoảng cách check in được giới hạn theo Địa điểm làm việc, vui lòng chọn địa điểm!")
            res.sudo().write({'en_location_id': en_location_id})
        if self.attendance_state == 'checked_out' and self.env.user.has_group('ngs_attendance.group_en_checkout_location'):
            if en_location_id and en_max_distance > 0:
                if not res.check_out_latitude and not res.check_out_longitude:
                    raise UserError("Bạn chưa cung cấp quyền truy cập vị trí, không thể check out")
                # if not en_location_id:
                #     raise UserError("Khoảng cách check out được giới hạn theo Địa điểm làm việc, vui lòng chọn địa điểm!")
            res.sudo().write({'en_location_checkout_id': en_location_id})

        if self.shift != 'ca_linh_hoat' and en_max_distance > 0:
            if not res.check_out_latitude and not res.check_out_longitude and self.attendance_state == 'checked_out':
                raise UserError("Bạn chưa cung cấp quyền truy cập vị trí, không thể check out")
            if self.attendance_state == 'checked_out' and res.en_checkout_distance and res.en_checkout_distance > en_max_distance:
                raise UserError("""Bạn đang ở quá xa địa điểm làm việc, không thể check out!"""
                    f"""\nĐịa điểm làm việc của bạn: {res.en_location_checkout_id.name}"""
                    f"""\nĐịa điểm checkout của bạn: {res.check_out_address}"""
                    f"""\nKhoảng cách {res.en_checkout_distance} km"""
                    f"""\nKhoảng cách cho phép {en_max_distance} km""")
            if self.attendance_state == 'checked_in' and res.en_checkin_distance and res.en_checkin_distance > en_max_distance:
                raise UserError(f"""Bạn đang ở quá xa địa điểm làm việc, không thể check in!"""
                    f"""\nĐịa điểm làm việc của bạn: {res.en_location_id.name}"""
                    f"""\nĐịa điểm checkin của bạn: {res.check_in_address}"""
                    f"""\nKhoảng cách {res.en_checkin_distance} km"""
                    f"""\nKhoảng cách cho phép {en_max_distance} km""")
        return res
