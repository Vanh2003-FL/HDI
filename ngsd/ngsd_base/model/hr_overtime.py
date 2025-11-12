from odoo import fields, models, api, _
from odoo.tools.date_utils import date_range
from dateutil.relativedelta import relativedelta
from pytz import timezone, UTC
from datetime import datetime, timedelta, time
from odoo.tools.float_utils import float_round
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression

READONLY_FIELD_STATES = {
    state: [('readonly', True)]
    for state in {'approved', 'requested', 'rejected', 'cancel'}
}
from math import modf


class HrOvertime(models.Model):
    _name = 'en.hr.overtime'
    _description = 'Yêu cầu tăng ca'
    _inherit = 'ngsd.approval'
    _order = 'date_from desc'

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        res = super(HrOvertime, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
        if groupby == ['state']:
            map_state = {
                'new': 0,
                'requested': 1,
                'approved': 2,
                'rejected': 3,
                'cancel': 4,
            }
            return sorted(res, key=lambda l: map_state.get(l.get('state'), 10))
        return res

    reason_refused = fields.Char(string='Lý do từ chối', copy=False, readonly=True)

    def _callback_reason_refused(self, reason):
        self.write({'reason_refused': reason})

    @api.depends_context('uid')
    @api.depends('employee_id')
    def _compute_sent_ok(self):
        for rec in self:
            rec.sent_ok = rec.sudo().employee_id and self.env.user == rec.sudo().employee_id.user_id

    def get_flow_domain(self):
        return [('model_id.model', '=', self._name), '|', ('project_ids', '=', False), ('project_ids', '=', self.task_id.project_id.id)]

    @api.constrains('employee_id', 'date_from', 'date_to')
    def _constrains_overlap_overtime(self):
        if any(rec.sudo().search_count([('id', '!=', rec.id), ('employee_id', '=', rec.employee_id.id), ('state', 'not in', ['cancel', 'rejected']),
                                        '|',
                                        '&', ('date_from', '<=', rec.date_from), ('date_to', '>=', rec.date_from),
                                        '&', ('date_from', '>=', rec.date_from), ('date_from', '<=', rec.date_to),
                                        ]) >= 1 for rec in self):
            raise ValidationError('Bạn đã có tăng ca trùng thời gian đã tạo')
        user_tz = timezone(self.env.user.tz if self.env.user.tz else 'UTC')
        holidays = self.env['resource.calendar.leaves'].search([('is_holiday', '=', True)])
        holidays_date = []
        for h in holidays:
            holidays_date.append([UTC.localize(h.date_from).astimezone(user_tz).replace(tzinfo=None).date(),
                                  UTC.localize(h.date_to).astimezone(user_tz).replace(tzinfo=None).date()])
        for rec in self:
            date_from = UTC.localize(rec.date_from).astimezone(user_tz).replace(tzinfo=None)
            is_holiday = False
            for h in holidays_date:
                if h[0] <= date_from.date() <= h[1]:
                    is_holiday = True
                    break
            if is_holiday:
                continue
            if rec.employee_id.resource_calendar_id.get_work_hours_count(rec.date_from, rec.date_to, compute_leaves=False):
                raise ValidationError('Chỉ được phép tạo tăng ca ngoài khung giờ làm việc!')

    @api.constrains('date_from', 'date_to')
    def _constrains_date(self):
        user_tz = timezone(self.env.user.tz if self.env.user.tz else 'UTC')
        holidays = self.env['resource.calendar.leaves'].search([('is_holiday', '=', True)])
        holidays_date = []
        for h in holidays:
            holidays_date.append([UTC.localize(h.date_from).astimezone(user_tz).replace(tzinfo=None).date(), UTC.localize(h.date_to).astimezone(user_tz).replace(tzinfo=None).date()])
        for rec in self:
            if not rec.date_from or not rec.date_to: continue
            date_from = UTC.localize(rec.date_from).astimezone(user_tz).replace(tzinfo=None)
            date_to = UTC.localize(rec.date_to).astimezone(user_tz).replace(tzinfo=None)
            if date_from and date_to and date_from > date_to:
                raise ValidationError('Bạn không thể chọn ngày bắt đầu lớn hơn ngày kết thúc')
            if date_from and date_to and date_from.date() != date_to.date():
                raise ValidationError('Người dùng chỉ được tăng ca trong ngày')

            # Check ngày nghỉ lễ
            is_holiday = False
            for h in holidays_date:
                if h[0] <= date_from.date() <= h[1]:
                    is_holiday = True
                    break
            if is_holiday:
                continue

            week_day = date_from.weekday()
            time_6h = date_from + relativedelta(hour=6, minute=0, second=0)
            time_14h = date_from + relativedelta(hour=14, minute=0, second=0)
            time_18h30 = date_from + relativedelta(hour=18, minute=30, second=0)

            if week_day <= 4 and (date_to > time_6h and date_from < time_18h30):
                raise UserError("Bạn không được tăng ca từ 6h đến 18h30")
            if week_day == 5 and (date_to > time_6h and date_from < time_14h):
                raise UserError("Bạn không được tăng ca từ 6h đến 14h")

    @api.onchange('date_from', 'date_to')
    def _onchange_date(self):
        if any(rec.date_from and rec.date_to and rec.date_from > rec.date_to for rec in self):
            return {'warning': {
                'title': 'Lỗi xác nhận',
                'message': 'Bạn không thể chọn ngày bắt đầu lớn hơn ngày kết thúc',
            }}

    can_request = fields.Boolean(string='🐧', compute='_compute_show_button')
    can_cancel = fields.Boolean(string='🐧', compute='_compute_show_button')
    can_approve = fields.Boolean(string='🐧', compute='_compute_show_button')
    can_reject = fields.Boolean(string='🐧', compute='_compute_show_button')
    can_new = fields.Boolean(string='🐧', compute='_compute_show_button')

    @api.depends_context('uid')
    @api.depends('employee_id', 'approver_id', 'state')
    def _compute_show_button(self):
        for rec in self:
            rec.can_request = self.env.user == rec.employee_id.user_id and rec.state in ['new']
            rec.can_cancel = self.env.user == rec.employee_id.user_id and rec.state in ['new']
            rec.can_approve = self.env.user in (rec.approver_id) and rec.state in ['requested']
            rec.can_reject = self.env.user in (rec.approver_id) and rec.state in ['requested']
            rec.can_new = rec.employee_id and self.env.user == rec.employee_id.user_id and rec.state in ['rejected', 'cancel']

    def to_overtime_overlimit(self):
        action = 'ngsd_base.hr_overtime_act'
        return self.open_form_or_tree_view(action, False, self.overtime_ids, {'import': False})

    count_overtime = fields.Integer(string='Tăng ca', compute_sudo=True, compute='_compute_count_overtime')
    overlimit_ok = fields.Boolean(string='Vượt quá số giờ tối đa', compute_sudo=True, compute='_compute_count_overtime')
    overlimit_unit = fields.Char(string='Đơn vị Vượt quá số giờ tối đa', compute_sudo=True, compute='_compute_count_overtime')
    overtime_ids = fields.Many2many(string='Tăng ca', compute_sudo=True, compute='_compute_count_overtime', comodel_name='en.hr.overtime')

    timesheet_ids = fields.One2many('account.analytic.line', 'ot_id', string='Timesheet')

    @api.constrains('employee_id', 'date_from', 'date_to')
    def _constrains_count_overtime(self):
        get_param = self.env['ir.config_parameter'].sudo().get_param
        # en_ot_warning = get_param('ngsd_base.en_ot_warning', 'ban')
        en_ot_warning = 'ban'
        if en_ot_warning != 'ban': return
        for rec in self:
            if rec.overlimit_ok: raise UserError(f'Bạn đã tăng ca vượt quá số giờ tối đa trong {rec.overlimit_unit}')

    department_id = fields.Many2one('hr.department', string='Trung tâm', related='employee_id.department_id')

    @api.depends('employee_id', 'date_from', 'date_to', 'create_uid')
    def _compute_count_overtime(self):
        get_param = self.env['ir.config_parameter'].sudo().get_param
        # en_ot_warning = get_param('ngsd_base.en_ot_warning', 'ban')
        en_ot_warning = 'ban'
        en_ot_day_limit = float(get_param('ngsd_base.en_ot_day_limit', 0))
        en_ot_month_limit = float(get_param('ngsd_base.en_ot_month_limit', 0))
        en_ot_year_limit = float(get_param('ngsd_base.en_ot_year_limit', 0))
        user_tz = timezone(self.env.user.tz if self.env.user.tz else 'UTC')
        holidays = self.env['resource.calendar.leaves'].search([('is_holiday', '=', True)])
        holidays_date = []
        for h in holidays:
            holidays_date.append([UTC.localize(h.date_from).astimezone(user_tz).replace(tzinfo=None).date(),
                                  UTC.localize(h.date_to).astimezone(user_tz).replace(tzinfo=None).date()])
        if en_ot_day_limit <= 0 and en_ot_month_limit <= 0 and en_ot_year_limit <= 0:
            self.count_overtime = 0
            self.overtime_ids = self.env['en.hr.overtime']
            self.overlimit_ok = False
            self.overlimit_unit = ''
        else:
            calendar_full_house = self.env.ref('ngsd_base.resource_calendar_full_house')
            for rec in self:
                if not rec.date_from or not rec.date_to or not rec.sudo().employee_id or rec.date_from > rec.date_to:
                    rec.count_overtime = 0
                    rec.overtime_ids = self.env['en.hr.overtime']
                    rec.overlimit_ok = False
                    rec.overlimit_unit = ''
                    continue
                tz = rec.sudo().employee_id.tz or rec.create_uid.tz or 'Asia/Ho_Chi_Minh'
                count_overtime = 0
                overlimit_ok = False
                overlimit_unit = ''
                overtime_ids = self.env['en.hr.overtime']
                date_from = min([rec.date_from.astimezone(timezone(tz)).date(), rec.date_to.astimezone(timezone(tz)).date()])
                date_to = max([rec.date_from.astimezone(timezone(tz)).date(), rec.date_to.astimezone(timezone(tz)).date()])
                if en_ot_day_limit > 0:
                    tz_datemin_from = timezone(tz).localize(datetime.combine(date_from, time.min)).astimezone(timezone('UTC')).replace(tzinfo=None)
                    tz_datemax_to = timezone(tz).localize(datetime.combine(date_to, time.max)).astimezone(timezone('UTC')).replace(tzinfo=None)
                    for tz_date in date_range(tz_datemin_from, tz_datemax_to, step=relativedelta(days=1)):
                        utc_date = tz_date.astimezone(timezone(tz)).date()
                        utc_date_from = timezone(tz).localize(datetime.combine(utc_date, time.min)).astimezone(timezone('UTC')).replace(tzinfo=None)
                        utc_date_to = timezone(tz).localize(datetime.combine(utc_date, time.max)).astimezone(timezone('UTC')).replace(tzinfo=None)
                        duration = rec.sudo().employee_id._get_work_days_data_batch(max([rec.date_from, utc_date_from]), min([rec.date_to, utc_date_to]), calendar=calendar_full_house).get(rec.employee_id.id, {}).get('hours')
                        overtimes = self.env['en.hr.overtime'].search([('id', '!=', rec._origin.id), ('employee_id', '=', rec.employee_id.id), ('state', 'not in', ['rejected', 'cancel']),
                                                                       '|',
                                                                       '&', ('date_from', '<=', utc_date_from), ('date_to', '>=', utc_date_from),
                                                                       '&', ('date_from', '>=', utc_date_from), ('date_from', '<=', utc_date_to), ])
                        for overtime in overtimes:
                            duration += overtime.sudo().employee_id._get_work_days_data_batch(max([overtime.date_from, utc_date_from]), min([overtime.date_to, utc_date_to]), calendar=calendar_full_house).get(overtime.employee_id.id, {}).get('hours')
                        date_from = UTC.localize(rec.date_from).astimezone(user_tz).replace(tzinfo=None)
                        date_to = UTC.localize(rec.date_to).astimezone(user_tz).replace(tzinfo=None)
                        is_holiday = False
                        week_day = date_from.weekday()
                        for h in holidays_date:
                            if h[0] <= date_from.date() <= h[1]:
                                is_holiday = True
                                break
                        if is_holiday or week_day in (5, 6):
                            continue
                        if duration > en_ot_day_limit:
                            count_overtime += len(overtimes)
                            overlimit_ok = True
                            overlimit_unit = 'ngày'
                            overtime_ids |= overtimes
                if overlimit_ok:
                    if rec._origin.id:
                        count_overtime += 1
                        overtime_ids |= rec
                    rec.count_overtime = count_overtime if en_ot_warning == 'warning' else 0
                    rec.overtime_ids = overtime_ids
                    rec.overlimit_ok = overlimit_ok
                    rec.overlimit_unit = overlimit_unit
                    continue

                if en_ot_month_limit > 0:
                    tz_datemin_from = timezone(tz).localize(datetime.combine((date_from + relativedelta(day=1)), time.min)).astimezone(timezone('UTC')).replace(tzinfo=None)
                    tz_datemax_to = timezone(tz).localize(datetime.combine((date_to + relativedelta(day=1, months=1, days=-1)), time.max)).astimezone(timezone('UTC')).replace(tzinfo=None)
                    for tz_date in date_range(tz_datemin_from, tz_datemax_to, step=relativedelta(months=1)):
                        utc_date = tz_date.astimezone(timezone(tz)).date()
                        utc_date_from = timezone(tz).localize(datetime.combine(utc_date, time.min)).astimezone(timezone('UTC')).replace(tzinfo=None)
                        utc_date_to = timezone(tz).localize(datetime.combine(utc_date + relativedelta(day=1, months=1, days=-1), time.max)).astimezone(timezone('UTC')).replace(tzinfo=None)
                        duration = rec.sudo().employee_id._get_work_days_data_batch(max([rec.date_from, utc_date_from]), min([rec.date_to, utc_date_to]), calendar=calendar_full_house).get(rec.employee_id.id, {}).get('hours')
                        overtimes = self.env['en.hr.overtime'].search([('id', '!=', rec._origin.id), ('employee_id', '=', rec.employee_id.id), ('state', 'not in', ['rejected', 'cancel']),
                                                                       '|',
                                                                       '&', ('date_from', '<=', utc_date_from), ('date_to', '>=', utc_date_from),
                                                                       '&', ('date_from', '>=', utc_date_from), ('date_from', '<=', utc_date_to), ])
                        for overtime in overtimes:
                            duration += overtime.sudo().employee_id._get_work_days_data_batch(max([overtime.date_from, utc_date_from]), min([overtime.date_to, utc_date_to]), calendar=calendar_full_house).get(overtime.employee_id.id, {}).get('hours')
                        if duration > en_ot_month_limit:
                            count_overtime += len(overtimes)
                            overlimit_ok = True
                            overlimit_unit = 'tháng'
                            overtime_ids |= overtimes
                if overlimit_ok:
                    if rec._origin.id:
                        count_overtime += 1
                        overtime_ids |= rec
                    rec.count_overtime = count_overtime if en_ot_warning == 'warning' else 0
                    rec.overtime_ids = overtime_ids
                    rec.overlimit_ok = overlimit_ok
                    rec.overlimit_unit = overlimit_unit
                    continue

                if en_ot_year_limit > 0:
                    tz_datemin_from = timezone(tz).localize(datetime.combine((date_from + relativedelta(day=1, month=1)), time.min)).astimezone(timezone('UTC')).replace(tzinfo=None)
                    tz_datemax_to = timezone(tz).localize(datetime.combine((date_to + relativedelta(day=1, month=1, years=1, days=-1)), time.max)).astimezone(timezone('UTC')).replace(tzinfo=None)
                    for tz_date in date_range(tz_datemin_from, tz_datemax_to, step=relativedelta(years=1)):
                        utc_date = tz_date.astimezone(timezone(tz)).date()
                        utc_date_from = timezone(tz).localize(datetime.combine(utc_date, time.min)).astimezone(timezone('UTC')).replace(tzinfo=None)
                        utc_date_to = timezone(tz).localize(datetime.combine(utc_date + relativedelta(day=1, month=1, years=1, days=-1), time.max)).astimezone(timezone('UTC')).replace(tzinfo=None)
                        duration = rec.sudo().employee_id._get_work_days_data_batch(max([rec.date_from, utc_date_from]), min([rec.date_to, utc_date_to]), calendar=calendar_full_house).get(rec.employee_id.id, {}).get('hours')
                        overtimes = self.env['en.hr.overtime'].search([('id', '!=', rec._origin.id), ('employee_id', '=', rec.employee_id.id), ('state', 'not in', ['rejected', 'cancel']),
                                                                       '|',
                                                                       '&', ('date_from', '<=', utc_date_from), ('date_to', '>=', utc_date_from),
                                                                       '&', ('date_from', '>=', utc_date_from), ('date_from', '<=', utc_date_to), ])
                        for overtime in overtimes:
                            duration += overtime.sudo().employee_id._get_work_days_data_batch(max([overtime.date_from, utc_date_from]), min([overtime.date_to, utc_date_to]), calendar=calendar_full_house).get(overtime.employee_id.id, {}).get('hours')
                        if duration > en_ot_year_limit:
                            count_overtime += len(overtimes)
                            overtime_ids |= overtimes
                            overlimit_ok = True
                            overlimit_unit = 'năm'

                if rec._origin.id and overlimit_ok:
                    count_overtime += 1
                    overtime_ids |= rec
                rec.count_overtime = count_overtime if en_ot_warning == 'warning' else 0
                rec.overtime_ids = overtime_ids
                rec.overlimit_ok = overlimit_ok
                rec.overlimit_unit = overlimit_unit

    def unlink(self):
        if any(rec.state in ['requested', 'approved'] for rec in self):
            raise ValidationError('Không thể xóa tăng ca ở trạng thái Đã gửi duyệt/Đã duyệt!')
        return super().unlink()

    def name_get(self):
        res = []
        for rec in self:
            res.append(
                (rec.id,
                 _("%(employee_name)s %(type_name)s : %(duration).2f tiếng",
                   employee_name=rec.sudo().employee_id.name,
                   type_name=rec.type_id.sudo().name or '',
                   duration=rec.time,
                   ))
            )
        return res

    en_nonproject_task_id = fields.Many2one('en.nonproject.task', string='Công việc ngoài dự án', states=READONLY_FIELD_STATES)

    task_id = fields.Many2one(string='Công việc', comodel_name='project.task', states=READONLY_FIELD_STATES)
    project_id = fields.Many2one(string='Dự án', comodel_name='project.project', related='task_id.project_id', store=True)
    project_code = fields.Char(related='project_id.en_code')

    technical_field_27817 = fields.Many2many(string='🚑', comodel_name='project.task', compute_sudo=False, compute='_compute_technical_field_27817')

    @api.depends('employee_id')
    def _compute_technical_field_27817(self):
        for rec in self:
            rec.technical_field_27817 = self.env['project.task'].search([('timesheet_ids.employee_id', '=', rec.employee_id.id), ('timesheet_ids.holiday_id', '=', False), ('timesheet_ids.global_leave_id', '=', False)])

    type_id = fields.Many2one(string='Loại tăng ca', comodel_name='en.hr.overtime.type', required=False, states=READONLY_FIELD_STATES)

    employee_id = fields.Many2one(string='Nhân viên', comodel_name='hr.employee', required=True, default=lambda self: self.env.user.employee_id, states=READONLY_FIELD_STATES)
    employee_barcode = fields.Char(string='Mã nhân viên', related='employee_id.barcode', store=True)

    approver_id = fields.Many2one(string='Người phê duyệt', domain="[('id','in',technical_field_27821)]", comodel_name='res.users', compute_sudo=True, compute='_compute_approver_id', store=True, readonly=False, required=False, states=READONLY_FIELD_STATES)

    technical_field_27821 = fields.Many2many(string='🤣', comodel_name='res.users', compute='_compute_technical_field_27821', compute_sudo=True)

    @api.depends('task_id')
    def _compute_technical_field_27821(self):
        for rec in self:
            technical_field_27821 = self.env['res.users']
            technical_field_27821 |= rec.task_id.project_id.user_id
            technical_field_27821 |= rec.task_id.project_id.en_project_manager_id
            technical_field_27821 |= self.env['res.users'].sudo().search([('groups_id', '=', self.env.ref('ngsd_base.group_gdkndu').id), ('employee_id.en_block_id', '=', rec.task_id.project_id.en_block_id.id)])
            rec.technical_field_27821 = technical_field_27821

    @api.depends('type_id', 'employee_id', 'task_id')
    def _compute_approver_id(self):
        for rec in self:
            approver_id = self.env['res.users']
            if not rec.type_id:
                rec.approver_id = approver_id
                continue
            approver_id = rec.sudo().employee_id.parent_id.user_id if rec.type_id.approve_type == 'manager' else rec.task_id.project_id.user_id if rec.type_id.approve_type == 'project_manager' else rec.type_id.approver_id
            rec.approver_id = approver_id

    is_other_employee = fields.Boolean('Nhân viên phòng ban khác', compute='_get_is_other_employee', store=True)

    @api.depends('employee_id', 'task_id')
    def _get_is_other_employee(self):
        for rec in self:
            rec.is_other_employee = rec.employee_id.department_id.manager_id.user_id != rec.task_id.project_id.en_project_block_id

    description = fields.Text(string='Mô tả', states=READONLY_FIELD_STATES)
    name = fields.Text(string='Mô tả')
    date = fields.Date(string='Ngày', compute='_get_date', store=True)
    time_start = fields.Float(string='Giờ bắt đầu', required=True, default=7)
    time_end = fields.Float(string='Giờ kết thúc', required=True, default=7)
    date_from = fields.Datetime(string='Ngày bắt đầu', required=True, states=READONLY_FIELD_STATES, compute='_get_date', store=True)
    date_to = fields.Datetime(string='Ngày kết thúc', required=True, states=READONLY_FIELD_STATES, compute='_get_date', store=True)
    time = fields.Float(string='Số giờ tăng ca', compute_sudo=True, compute='_compute_time', store=True)
    en_overtime_plan_id = fields.Many2one('en.overtime.plan', string='Kế hoạch OT', domain="[('id', 'in', en_overtime_plan_domain), ('state', '=', 'approved')]", required=1)
    en_overtime_plan_domain = fields.Many2many('en.overtime.plan', compute='_get_en_overtime_plan_domain')

    def recompute_date_old(self):
        for rec in self:
            rec.date = rec.date_from.date()
            if rec.date_from:
                date_from = rec.date_from + relativedelta(hours=7)
                rec.time_start = date_from.hour + date_from.minute / 60
            if rec.date_to:
                date_to = rec.date_to + relativedelta(hours=7)
                rec.time_end = date_to.hour + date_to.minute / 60
            if (rec.date_from + relativedelta(hours=7)).date() != (rec.date_to + relativedelta(hours=7)).date():
               raise UserError('Ngày bắt đầu và ngày kết thúc phải cùng 1 ngày')

    @api.depends('date_from', 'employee_id', 'timesheet_ids', 'time_start', 'time_end')
    def _get_date(self):
        for rec in self:
            rec.date = rec.timesheet_ids[0].date
            date_from = date_to = False
            if rec.date:
                date_from = rec.date + rec.float_to_relativedelta(rec.time_start) - relativedelta(hours=7)
                date_to = rec.date + rec.float_to_relativedelta(rec.time_end) - relativedelta(hours=7)
            rec.date_from = date_from
            rec.date_to = date_to

    @api.depends('task_id', 'en_nonproject_task_id', 'date_from', 'date_to', 'employee_id')
    def _get_en_overtime_plan_domain(self):
        for rec in self:
            ext_domain = []
            domain = [('create_uid', '=', rec.employee_id.user_id.id), ('en_date', '=', rec.date)]
            rec.en_overtime_plan_domain = False
            if rec.task_id and not rec.en_nonproject_task_id:
                ext_domain = [('en_work_id', '=', rec.task_id.id)]
                domain += ext_domain
                rec.en_overtime_plan_domain = self.env['en.overtime.plan'].search(domain)
            if rec.en_nonproject_task_id and not rec.task_id:
                ext_domain += [('en_work_nonproject_id', '=', rec.en_nonproject_task_id.id)]
                domain += ext_domain
                rec.en_overtime_plan_domain = self.env['en.overtime.plan'].search(domain)

    @api.onchange('en_overtime_plan_id')
    def change_en_overtime_plan_id(self):
        self.description = self.en_overtime_plan_id.en_reason_ot
        self.name = self.en_overtime_plan_id.en_reason_ot

    @api.constrains('en_overtime_plan_id', 'date_from', 'date_to', 'time')
    def check_from_en_overtime_plan_id(self):
        for rec in self:
            if not rec.en_overtime_plan_id.en_date:
                raise UserError('Bạn cần chọn thời gian OT trong kế hoạch')
            if not (rec.date_from.astimezone(timezone(self.env.user.tz or "Asia/Ho_Chi_Minh")).date() <= rec.en_overtime_plan_id.en_date <= rec.date_to.astimezone(timezone(self.env.user.tz or "Asia/Ho_Chi_Minh")).date()):
                raise UserError('Bạn cần chọn lại thời gian OT theo kế hoạch')
            if rec.time > rec.en_overtime_plan_id.en_hours:
                raise UserError('Số giờ tăng ca không được lớn hơn số giờ OT theo kế hoạch')

    # @api.onchange('name')
    # def change_name(self):
    #     self.description = self.name

    def float_to_time(self, hours, moment='am'):
        """ Convert a number of hours into a time object. """
        if hours == 12.0 and moment == 'pm':
            return time.max
        fractional, integral = modf(hours)
        if moment == 'pm':
            integral += 12
        return time(int(integral), int(float_round(60 * fractional, precision_digits=0)), 0)

    def float_to_relativedelta(self, float_hour):
        if float_hour == 24:
            float_hour = 23.9999
        minute = (float_hour % 1) * 60
        second = (minute % 1) * 60
        return relativedelta(hour=int(float_hour), minute=int(minute), second=int(second), microsecond=0)

    def time_to_float(self, t):
        return float_round(t.hour + t.minute / 60 + t.second / 3600, precision_digits=2)

    def timedelta_to_float(self, td):
        return float_round(td.total_seconds() / timedelta(hours=1).total_seconds(), precision_digits=2)

    @api.depends('date_from', 'date_to')
    def _compute_time(self):
        for rec in self:
            time = 0
            if not rec.date_from or not rec.date_to:
                rec.time = time
                continue
            time = rec.timedelta_to_float(max([rec.date_from, rec.date_to]) - min([rec.date_from, rec.date_to]))
            month_leave_intervals = rec.employee_id.list_leaves(rec.date_from, rec.date_to)
            if rec.date.weekday() == 6 or rec.date.weekday() == 5 or any(leave.is_holiday for day, hours, leaves in month_leave_intervals for leave in leaves):
                hour_from = self.time_to_float(rec.date_from + relativedelta(hours=7))
                hour_to = self.time_to_float(rec.date_to + relativedelta(hours=7))
                if time > 10 and ((hour_from < 13.5 and hour_to > 12) or (hour_from < 19.5 and hour_to > 18)):
                    time -= 1.5
                if time < 10 and ((hour_from < 13 and hour_to > 12) or (hour_from < 19 and hour_to > 18)):
                    time -= 1
            if time < 0:
                time = 0
            rec.time = time

    state = fields.Selection(string='Trạng thái', selection=[('new', 'Mới'), ('requested', 'Đã gửi duyệt'), ('approved', 'Đã duyệt'), ('rejected', 'Từ chối'), ('cancel', 'Hủy')], default='new', required=True, copy=False, readonly=True)

    def draft_state(self):
        return 'new'

    def sent_state(self):
        return 'requested'

    def approved_state(self):
        return 'approved'

    def refused_state(self):
        return 'rejected'

    def button_requested(self):
        self._constrains_overlap_overtime()
        for rec in self:
            if not rec.can_request: continue
            rec.sudo().write({'state': 'requested'})
            rec.send_notify('Bạn có yêu cầu tăng ca cần phê duyệt', rec.approver_id, f'Yêu cầu tăng ca: {rec.sudo().employee_id.name} {rec.date_from.astimezone(timezone(rec.approver_id.tz or "Asia/Ho_Chi_Minh")).date().strftime("%d/%m/%Y")}')

    def button_cancel(self):
        for rec in self:
            if not rec.can_cancel: continue
            rec.sudo().write({'state': 'cancel'})

    def button_rejected(self):
        for rec in self:
            if not rec.can_reject: continue
            rec.sudo().write({'state': 'rejected'})
            rec.sudo().send_notify('Yêu cầu tăng ca của bạn bị từ chối', rec.sudo().employee_id.user_id, f'Yêu cầu tăng ca bị từ chối: {rec.date_from.astimezone(timezone(self.env.user.tz or "Asia/Ho_Chi_Minh")).date().strftime("%d/%m/%Y")}')

    def button_new(self):
        for rec in self:
            if not rec.can_new: continue
            rec.sudo().write({'state': 'new'})

    def action_approve_overtime(self):
        if any(rec.state != 'requested' or not rec.approve_ok for rec in self):
            raise UserError('Bản ghi của bạn không đủ điều kiện duyệt')
        for rec in self:
            rec.button_approved()

    def action_refused_overtime(self):
        if any(rec.state != 'requested' or not rec.approve_ok for rec in self):
            raise UserError('Bản ghi của bạn không đủ điều kiện để từ chối')
        for rec in self:
            if rec.state_change('refused'):
                rec.sudo().write({
                    'state': 'rejected'
                })

    detail_ids = fields.One2many('en.hr.overtime.detail', 'overtime_id', string='Chi tiết tăng ca', compute='_compute_overtime_details', store=True)

    type_ids = fields.Many2many(string='Loại tăng ca', comodel_name='en.hr.overtime.type', compute='_get_type_ids', store=True)
    detail_count = fields.Integer(string='Số loại tăng ca', compute='_get_type_ids', store=True)
    rate = fields.Float(string='Hệ số', compute_sudo=True, compute='_compute_based_on_type', store=True)

    en_task_type = fields.Selection(related="en_nonproject_task_id.en_task_type", string='Loại công việc', store=True)

    @api.depends('detail_ids')
    def _get_type_ids(self):
        for rec in self:
            rec.type_ids = rec.detail_ids.mapped('type_id')
            rec.detail_count = len(rec.detail_ids)
            rec.rate = rec.detail_ids.rate if len(rec.detail_ids) == 1 else 0

    @api.depends('date_from', 'date_to', 'date')
    def _compute_overtime_details(self):
        for rec in self:
            detail_ids = [(5, 0, 0)]
            if rec.date_from and rec.date_to:
                # Fetch holidays
                cot = False
                morning = self.env['en.hr.overtime.detail'].sudo().search([('overtime_id.employee_id', '=', rec.employee_id.id), ('overtime_id.state', 'in', ['approved']), ('overtime_id.date', '=', rec.date), ('day_period', '=', 'morning')])
                if morning:
                    cot = True
                holidays = self.env['resource.calendar.leaves'].search([('is_holiday', '=', True), ('date_from_convert', '<=', rec.date), ('date_to_convert', '>=', rec.date)])
                if holidays:
                    intervals = rec._get_interval_from_date([('type_id.is_holiday', '=', True)])
                else:
                    intervals = rec._get_interval_from_date([('date', 'in', [str(rec.date.weekday())]), ('type_id.is_holiday', '=', False)])
                for interval in intervals:
                    interval_start, interval_end, rate, attendance = interval
                    if attendance.day_period == 'morning':
                        cot = True
                for interval in intervals:
                    interval_start, interval_end, rate, attendance = interval
                    if attendance.day_period == 'night' and cot:
                        rate = attendance.rate_cot
                    detail_ids.append((0, 0, {
                        'time_start': interval_start - relativedelta(hours=7),
                        'time_end': interval_end - relativedelta(hours=7),
                        'type_id': attendance.type_id.id,
                        'rate': rate,
                        'day_period': attendance.day_period,
                    }))
            rec.detail_ids = detail_ids

    def _get_interval_from_date(self, domain):
        start = self.date_from + relativedelta(hours=7)
        stop = self.date_to + relativedelta(hours=7)
        segments = []
        current_start = start
        attendances = self.env['en.hr.overtime.attendance'].search(domain, order='time_start')
        for attendance in attendances:
            interval_start, interval_end, rate = (attendance.time_start, attendance.time_end, attendance.rate)
            interval_start_time = start + self.float_to_relativedelta(interval_start)
            interval_end_time = start + self.float_to_relativedelta(interval_end)
            if interval_end_time < start or interval_start_time > stop:
                continue
            if current_start < interval_start_time:
                if current_start != interval_start_time:
                    segments.append((max(current_start, start), min(interval_start_time, stop), 1, self.env['en.hr.overtime.attendance']))  # Hệ số 1 cho các đoạn không thuộc khoảng thời gian

            if interval_start_time < stop and interval_end_time > start:
                segment_start = max(start, interval_start_time)
                segment_end = min(stop, interval_end_time)
                if segment_start < segment_end:
                    segments.append((segment_start, segment_end, rate, attendance))

            current_start = interval_end_time

        if current_start < stop:
            if current_start != stop:
                segments.append((current_start, stop, 1, self.env['en.hr.overtime.attendance']))  # Hệ số 1 cho thời gian còn lại

        # Xử lý các đoạn trùng lặp bằng cách chọn đoạn có hệ số cao hơn
        final_segments = []
        for segment in segments:
            if final_segments and final_segments[-1][1] > segment[0]:
                if final_segments[-1][2] < segment[2]:
                    final_segments[-1] = (final_segments[-1][0], segment[0], final_segments[-1][2], final_segments[-1][3])
                    final_segments.append(segment)
                else:
                    final_segments[-1] = (final_segments[-1][0], segment[1], final_segments[-1][2], final_segments[-1][3])
            else:
                final_segments.append(segment)

        # Loại bỏ các đoạn có thời gian bắt đầu bằng thời gian kết thúc
        final_segments = [segment for segment in final_segments if segment[0] != segment[1]]

        return final_segments


class HrOvertimeDetail(models.Model):
    _name = 'en.hr.overtime.detail'
    _description = 'Chi tiết tăng ca'

    overtime_id = fields.Many2one('en.hr.overtime', string='Tăng ca', required=True, ondelete='cascade')
    time_start = fields.Datetime(string='Ngày bắt đầu', required=True)
    time_end = fields.Datetime(string='Ngày kết thúc', required=True)
    hour_start = fields.Float(string='Bắt đầu', compute='_compute_total_hour', store=True)
    hour_end = fields.Float(string='Kết thúc', compute='_compute_total_hour', store=True)
    total_hour = fields.Float(string='Số giờ', compute='_compute_total_hour', store=True)
    type_id = fields.Many2one(string='Loại', comodel_name='en.hr.overtime.type', required=False)
    rate = fields.Float(string='Hệ số', required=True)
    day_period = fields.Selection([('morning', 'Sáng'), ('night', 'Tối')], required=False, default='night')

    @api.depends('time_start', 'time_end')
    def _compute_total_hour(self):
        for rec in self:
            total_hour = 0
            hour_start = False
            hour_end = False
            if rec.time_start and rec.time_end:
                time_start = rec.time_start + relativedelta(hours=7)
                time_end = rec.time_end + relativedelta(hours=7)
                total_hour = rec.overtime_id.timedelta_to_float(time_end - time_start)
                hour_start = time_start.hour + time_start.minute / 60
                hour_end = time_end.hour + time_end.minute / 60
            rec.total_hour = total_hour
            rec.hour_start = hour_start
            rec.hour_end = hour_end
