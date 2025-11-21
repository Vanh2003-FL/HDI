from ast import literal_eval
from odoo import models, fields, api, exceptions
from odoo import _
from datetime import timedelta, datetime, time, date
from dateutil.relativedelta import relativedelta
from collections import defaultdict
from odoo.tools import config, date_utils, get_lang, html2plaintext
from pytz import timezone, UTC
from lxml import etree
import json
from odoo.exceptions import AccessError, UserError, ValidationError
# Domain, TRUE_LEAF, FALSE_LEAF removed - not available in Odoo 18

READONLY_STATES = {
    'approved': [('readonly', True)],
}

try:
    from odoo.addons.project.models.project_task import Task
except ImportError:
    try:
        from odoo.addons.project.models.project import Task
    except ImportError:
        # Fallback for different Odoo versions
        Task = None

def new_write(self, vals):
    # if len(self) == 1:
    #     handle_history_divergence(self, 'description', vals)
    portal_can_write = False
    if self.env.user.has_group('base.group_portal') and not self.env.su:
        # Check if all fields in vals are in SELF_WRITABLE_FIELDS
        self._ensure_fields_are_accessible(vals.keys(), operation='write', check_group_user=False)
        self.check_access_rights('write')
        self.check_access_rule('write')
        portal_can_write = True

    now = fields.Datetime.now()
    if 'parent_id' in vals and vals['parent_id'] in self.ids:
        raise UserError(_("Bạn không thể đặt một nhiệm vụ làm nhiệm vụ chính của nó."))
    if 'active' in vals and not vals.get('active') and any(self.mapped('recurrence_id')):
        # TODO: show a dialog to stop the recurrence
        raise UserError(_('You cannot archive recurring tasks. Please disable the recurrence first.'))
    if 'recurrence_id' in vals and vals.get('recurrence_id') and any(not task.active for task in self):
        raise UserError(_('Archived tasks cannot be recurring. Please unarchive the task first.'))
    # stage change: update date_last_stage_update
    if 'stage_id' in vals:
        vals.update(self.update_date_end(vals['stage_id']))
        vals['date_last_stage_update'] = now
        # reset kanban state when changing stage
        if 'kanban_state' not in vals:
            vals['kanban_state'] = 'normal'
    # user_ids change: update date_assign
    if vals.get('user_ids') and 'date_assign' not in vals:
        vals['date_assign'] = now

    # recurrence fields
    rec_fields = vals.keys() & self._get_recurrence_fields()
    if rec_fields:
        rec_values = {rec_field: vals[rec_field] for rec_field in rec_fields}
        for task in self:
            if task.recurrence_id:
                task.recurrence_id.write(rec_values)
            elif vals.get('recurring_task'):
                rec_values['next_recurrence_date'] = fields.Datetime.today()
                recurrence = self.env['project.task.recurrence'].create(rec_values)
                task.recurrence_id = recurrence.id

    if 'recurring_task' in vals and not vals.get('recurring_task'):
        self.recurrence_id.unlink()

    tasks = self
    recurrence_update = vals.pop('recurrence_update', 'this')
    if recurrence_update != 'this':
        recurrence_domain = []
        if recurrence_update == 'subsequent':
            for task in self:
                # Combine domains using OR operator
                recurrence_domain = recurrence_domain + ['|', ('recurrence_id', '=', task.recurrence_id.id), ('create_date', '>=', task.create_date)]
        else:
            recurrence_domain = [('recurrence_id', 'in', self.recurrence_id.ids)]
        tasks |= self.env['project.task'].search(recurrence_domain)

    # The sudo is required for a portal user as the record update
    # requires the write access on others models, as rating.rating
    # in order to keep the same name than the task.
    if portal_can_write:
        tasks = tasks.sudo()

    # Track user_ids to send assignment notifications
    old_user_ids = {t: t.user_ids for t in self}

    result = super(Task, tasks).write(vals)

    self._task_message_auto_subscribe_notify({task: task.user_ids - old_user_ids[task] - self.env.user for task in self})

    if 'user_ids' in vals:
        tasks._populate_missing_personal_stages()

    # rating on stage
    if 'stage_id' in vals and vals.get('stage_id'):
        tasks.filtered(lambda x: x.project_id.rating_active and x.project_id.rating_status == 'stage')._send_task_rating_mail(force_send=True)
    # Note: display_project_id field handling removed for Odoo 18 compatibility
    return result

# Only monkey patch if Task class was imported successfully
if Task is not None:
    Task.write = new_write


class NGSLeave(models.Model):
    _name = 'ngs.leave.allocation'
    _description = 'Phân bổ nghỉ phép'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Mã phân bổ', required=True)
    holiday_status_id = fields.Many2one("hr.leave.type", string=" Loại nghỉ phép", required=True, ondelete='cascade')
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('confirm', 'Đã xác nhận'),],
        string='Trạng thái', required=True, default='draft')
    holiday_type = fields.Selection([
        ('employee', 'Theo nhân viên'),
        ('company', 'Theo công ty'),
        ('department', 'Theo phòng ban'),
        ('category', 'Theo thẻ nhân viên')],
        string='Chế độ', required=True, default='employee')
    employee_ids = fields.Many2many('hr.employee', string='Nhân viên')
    mode_company_id = fields.Many2one('res.company', string='Company Mode')
    department_id = fields.Many2one('hr.department', string='Trung tâm/ ban')
    category_id = fields.Many2one('hr.employee.category', string='Employee Tag')
    nextcall = fields.Date("Ngày thực hiện tiếp theo", default=False, required=True)

    interval_number = fields.Integer('Chu kỳ', required=True)
    interval_type = fields.Selection([
        ('days', 'Ngày'),
        ('weeks', 'Tuần'),
        ('months', 'Tháng'),
        ('years', 'Năm'),
    ], string='Interval Unit', default='weeks', required=True)
    number_of_days = fields.Float('Số ngày phân bổ', default=1, required=True)

    interval_number_ext = fields.Integer('Khoảng thời gian hiệu lực thêm')
    interval_type_ext = fields.Selection([
        ('days', 'Ngày'),
        ('weeks', 'Tuần'),
        ('months', 'Tháng'),
        ('years', 'Năm'),
    ], string='Interval Unit', default='weeks')

    period_number = fields.Integer('Số chu kỳ', required=True, default=1)

    @api.constrains('interval_number', 'number_of_days', 'period_number')
    def check_has_interval_number(self):
        for rec in self:
            if rec.interval_number <= 0:
                raise exceptions.ValidationError('Chu kỳ phải lớn hơn 0')

            if rec.number_of_days <= 0:
                raise exceptions.ValidationError('Số ngày phân bổ phải lớn hơn 0')

            if rec.period_number <= 0:
                raise exceptions.ValidationError('Số chu kỳ phải lớn hơn 0')

    def cron_allocation(self):
        today = fields.Date.Date.Date.context_today(self)
        for rec in self.search([('nextcall', '<=', today), ('state', '=', 'confirm'), ('holiday_status_id.requires_allocation', '=', 'yes')]):
            rec.allocate_leave()

    def allocate_leave(self):
        today = fields.Date.Date.Date.context_today(self)
        for rec in self:
            if rec.state != 'confirm':
                continue
            if not rec.number_of_days:
                continue
            if rec.nextcall > today:
                continue
            if rec.holiday_status_id.requires_allocation != 'yes':
                continue
            for period in range(rec.period_number):
                period_day = rec.nextcall + timedelta(**{rec.interval_type: rec.interval_number * period})
                domain_allocation = [('ngs_allocation_id', '=', rec.id), ('date_from', '=', period_day)]
                if self.env['hr.leave.allocation'].search_count(domain_allocation):
                    continue
                date_to = period_day + timedelta(**{rec.interval_type: rec.interval_number})
                if rec.interval_number_ext and rec.interval_type_ext:
                    date_to += timedelta(**{rec.interval_type_ext: rec.interval_number_ext})
                date_to -= timedelta(days=1)

                allocation = self.env['hr.leave.allocation'].create({
                    'name': rec.name,
                    'ngs_allocation_id': rec.id,
                    'multi_employee': True,
                    'holiday_status_id': rec.holiday_status_id.id,
                    'holiday_type': rec.holiday_type,
                    'employee_ids': [(6, 0, rec.employee_ids.ids)],
                    'mode_company_id': rec.mode_company_id.id,
                    'department_id': rec.department_id.id,
                    'category_id': rec.category_id.id,
                    'date_from': rec.nextcall if period == 0 else period_day,
                    'date_to': date_to,
                    'number_of_days': rec.number_of_days,
                })
                allocation.action_confirm()
                allocation.action_validate()
            nextcall = rec.nextcall + timedelta(**{rec.interval_type: rec.interval_number * rec.period_number})
            while nextcall < today:
                nextcall += timedelta(**{rec.interval_type: rec.interval_number})
            rec.nextcall = nextcall

    def button_confirm(self):
        self.write({'state': 'confirm'})


class HolidaysAllocation(models.Model):
    _inherit = "hr.leave.allocation"

    ngs_allocation_id = fields.Many2one('ngs.leave.allocation', string='Phân bổ nghỉ phép', index=True)
    has_exclude_employee = fields.Boolean(string='Loại trừ nhân viên', default=False)
    exclude_employee_domain = fields.Char(string='Loại trừ nhân viên', default="[]")
    stop_at = fields.Date('Ngày kết thúc', compute='_get_stop_at', store=True)

    @api.depends('date_to')
    def _get_stop_at(self):
        for rec in self:
            rec.stop_at = rec.date_to

    def _action_validate_create_childs(self):
        childs = self.env['hr.leave.allocation']
        # In the case we are in holiday_type `employee` and there is only one employee we can keep the same allocation
        # Otherwise we do need to create an allocation for all employees to have a behaviour that is in line
        # with the other holiday_type
        if self.state == 'validate' and (self.holiday_type in ['category', 'department', 'company'] or
            (self.holiday_type == 'employee' and len(self.employee_ids) > 1)):
            if self.holiday_type == 'employee':
                employees = self.employee_ids
            elif self.holiday_type == 'category':
                employees = self.category_id.employee_ids
            elif self.holiday_type == 'department':
                employees = self.department_id.member_ids
            else:
                employees = self.env['hr.employee'].search([('company_id', '=', self.mode_company_id.id)])
            if self.has_exclude_employee and (self.exclude_employee_domain or '[]') != '[]':
                exclude_employee_domain = literal_eval(self.exclude_employee_domain)
                employees -= employees.filtered_domain(exclude_employee_domain)

            allocation_create_vals = self._prepare_holiday_values(employees)
            childs += self.with_context(
                mail_notify_force_send=False,
                mail_activity_automation_skip=True
            ).create(allocation_create_vals)
            if childs:
                childs.action_validate()
        return childs

    def cron_auto_update_missing_employee(self):
        today = datetime.combine(fields.Date.today(), time(0, 0, 0))
        allocations = self.search(
            [('allocation_type', '=', 'accrual'), ('state', '=', 'validate'), ('accrual_plan_id', '!=', False),
             ('holiday_type', 'in', ['category', 'department', 'company']),
             '|', ('stop_at', '=', False), ('stop_at', '>', fields.Datetime.now()),
             '|', ('nextcall', '=', False), ('nextcall', '<=', today)])
        for a in allocations:
            a.with_context(update_missing_employee=True)._action_validate_create_childs()

    def _prepare_holiday_values(self, employees):
        self.ensure_one()
        res = []
        today = fields.Date.Date.Date.context_today(self)
        for employee in employees:
            if self._context.get('update_missing_employee'):
                if employee.en_date_start > today:
                    continue
                if self.search([('parent_id', '=', self.id), ('employee_id', '=', employee.id)]):
                    continue
            date_from = self.date_from
            number_of_days = self.number_of_days
            if self._context.get('fill_date_now'):
                if date_from < today:
                    date_from = today + relativedelta(day=1)
                number_of_days = 1
                if today.day > 15:
                    number_of_days = 0.5
            res.append({
                'name': self.name,
                'holiday_type': 'employee',
                'holiday_status_id': self.holiday_status_id.id,
                'notes': self.notes,
                'number_of_days': number_of_days,
                'parent_id': self.id,
                'employee_id': employee.id,
                'employee_ids': [(6, 0, [employee.id])],
                'state': 'confirm',
                'allocation_type': self.allocation_type,
                'date_from': date_from,
                'date_to': self.stop_at,
                'accrual_plan_id': self.accrual_plan_id.id,
                'advance_leave': self.advance_leave,
                'use_advance_leave': self.use_advance_leave,
            })
        return res

    @api.model
    def _update_accrual(self):
        """
            Method called by the cron task in order to increment the number_of_days when
            necessary.
        """
        # Get the current date to determine the start and end of the accrual period
        today = datetime.combine(fields.Date.Date.Date.context_today(self), time(0, 0, 0))
        this_year_first_day = today + relativedelta(day=1, month=1)
        end_of_year_allocations = self.search(
        [('allocation_type', '=', 'accrual'), ('state', '=', 'validate'), ('accrual_plan_id', '!=', False), ('employee_id', '!=', False),
            '|', ('date_to', '=', False), ('date_to', '>', fields.Datetime.now()), ('lastcall', '<', this_year_first_day)])
        end_of_year_allocations._end_of_year_accrual()
        end_of_year_allocations.flush()
        allocations = self.search(
        [('allocation_type', '=', 'accrual'), ('state', '=', 'validate'), ('accrual_plan_id', '!=', False), ('employee_id', '!=', False),
            '|', ('stop_at', '=', False), ('stop_at', '>', fields.Datetime.now()),
            '|', ('nextcall', '=', False), ('nextcall', '<=', today)])
        allocations._process_accrual_plans()


class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    code = fields.Char(string='Mã', required=True)
    ngs_allocation_ids = fields.One2many('ngs.leave.allocation', 'holiday_status_id', string='Phân bổ nghỉ phép')


class HrLeave(models.Model):
    _name = 'hr.leave'
    _inherit = ['hr.leave', 'ngsd.approval','mail.thread', 'mail.activity.mixin']

    leave_manager_id = fields.Many2one(related='employee_id.leave_manager_id', string='Người phê duyệt')
    project_id = fields.Many2one('project.project', string='Dự án')
    can_approve = fields.Boolean(compute_sudo=True)
    employee_barcode = fields.Char(string='Mã nhân viên', related='employee_id.barcode', store=True)
    state = fields.Selection(compute=False, default='draft')
    reason_refused = fields.Char('Lý do từ chối', readonly=1)
    leave_code = fields.Char(related='holiday_status_id.code', string='Mã loại nghỉ phép')

    def sent_state(self):
        return 'confirm'

    def approved_state(self):
        return 'validate'

    def refused_state(self):
        return 'refuse'

    def button_to_approve(self):
        if self.filtered(lambda holiday: holiday.state != 'draft'):
            raise UserError('Chỉ Gửi duyệt các nghỉ phép ở trạng thái Mới.')
        if self.filtered(lambda holiday: holiday._get_leaves_on_public_holiday()):
            raise UserError('Nghỉ phép ngoài thời gian làm việc hoặc không có thời lượng nghỉ')
        self.button_sent()
        en_status_hr = ['inactive', 'semi-inactive', 'maternity-leave']
        if not self.en_next_approver_ids:
            raise ValidationError("Không tìm thấy người duyệt nghỉ phép trong quy trình duyệt,"
                                  " vui lòng liên hệ HR để xử lý.")
        en_approver_hr_statuses = self.sudo().with_context(active_test=False).en_next_approver_ids.mapped(
            'employee_id.en_status_hr')
        if any(status in en_status_hr for status in en_approver_hr_statuses):
            raise UserError("Người duyệt nghỉ phép đang không hoạt động, vui lòng liên hệ HR để xử lý.")
        self.write({'state': 'confirm'})
        self.activity_update()

    def button_approved(self):
        if self.filtered(lambda holiday: holiday.state != 'confirm'):
            raise UserError('Chỉ duyệt các nghỉ phép ở trạng thái Chờ duyệt.')
        res = super().button_approved()
        if res:
            self._validate_leave_request()
            self.activity_update()
        return res

    def button_mass_approved(self):
        if not self.env.user.has_group('hr.group_hr_manager'):
            raise exceptions.ValidationError('Bạn không có quyền duyệt nghỉ phép')
        for rec in self:
            rec.en_approve_line_ids.filtered(lambda x: x.state == 'sent').write({'state': 'approved', 'user_id': self.env.user.id, 'date': fields.Datetime.now()})
            rec.sudo().write({'state': rec.approved_state()})
            rec._validate_leave_request()
            rec.activity_update()

    def _callback_reason_refused(self, reason):
        self.write({'reason_refused': reason})
        self.mapped('meeting_id').write({'active': False})
        # If a category that created several holidays, cancel all related
        linked_requests = self.mapped('linked_request_ids')
        if linked_requests:
            linked_requests.action_refuse()
        self.activity_update()

    @api.constrains('request_date_from')
    def _check_request_date_from(self):
        for rec in self:
            if not self.env.user.has_group('ngsd_base.group_userhr') and rec.request_date_from and rec.request_date_from < (fields.Date.Date.Date.context_today(self) + relativedelta(day=1)):
                raise UserError('Bạn không được xin nghỉ trong tháng ở quá khứ. Vui lòng liên hệ quản trị viên để được hỗ trợ.')

            today = fields.Date.Date.Date.context_today(self)
            if not self.env.user.has_group('ngsd_base.group_userhr') and rec.request_date_to and rec.request_date_to >= (today + relativedelta(months=6 - (today.month - 1) % 3, day=1)):
                raise UserError('Bạn chỉ được xin nghỉ đến hết quý tới. Vui lòng liên hệ quản trị viên để được hỗ trợ.')

    @api.depends('state', 'employee_id', 'department_id')
    def _compute_can_approve(self):
        for holiday in self:
            if (holiday.employee_ids | holiday.employee_id).leave_manager_id:
                if self.env.user in (holiday.employee_ids | holiday.employee_id).leave_manager_id:
                    holiday.can_approve = True
                else:
                    holiday.can_approve = False
            else:
                try:
                    if holiday.state == 'confirm' and holiday.validation_type == 'both':
                        holiday._check_approval_update('validate1')
                    else:
                        holiday._check_approval_update('validate')
                except (AccessError, UserError):
                    holiday.can_approve = False
                else:
                    holiday.can_approve = True

    def action_approve(self):
        user_tz = timezone(self.env.user.tz if self.env.user.tz else 'UTC')
        # for holiday in self:
        #     datetime_start = UTC.localize(holiday.date_from).astimezone(user_tz).replace(tzinfo=None, hour=0, minute=0, second=0)
        #     datetime_end = UTC.localize(holiday.date_to).astimezone(user_tz).replace(tzinfo=None, hour=23, minute=59, second=59)
        #     for date_step in date_utils.date_range(datetime_start, datetime_end, relativedelta(days=1)):
        #         date_from = max(date_step, holiday.date_from)
        #         date_to = min(date_step.replace(hour=23, minute=59, second=59), holiday.date_to)
        #         work_hours = holiday.employee_id.resource_calendar_id.get_work_hours_count(date_from, date_to, compute_leaves=False)
        #         timesheets = self.env['account.analytic.line'].search([('employee_id', '=', holiday.employee_id.id), ('date', '>=', date_from.date()), ('date', '<=', date_to.date()), ('en_state', '!=', 'cancel')])
        #         timesheet_hours = sum(ts.unit_amount for ts in timesheets) if timesheets else 0
        #         if (work_hours + timesheet_hours) > 8:
        #             raise ValidationError('Bạn không thể duyệt nghỉ phép vì đã có timesheet trong quãng thời gian nghỉ')

        holidays = super().action_approve()
        need_recomputes = self.env['en.technical.model']
        for holiday in self:
            domain = [('date', '>=', holiday.date_from), ('date', '<=', holiday.date_to)]
            if holiday.employee_id:
                domain += [('employee_id', '=', holiday.employee_id.id)]
            need_recomputes |= self.env['en.technical.model'].search(domain)
        need_recomputes._compute_technumber()
        return holidays

    @api.constrains('holiday_status_id', 'employee_id')
    def check_employee_permanent_p(self):
        for rec in self:
            if rec.employee_id and rec.employee_id.state_hr_employee != 'permanent' and rec.holiday_status_id.code == 'P':
                raise UserError('Chỉ nhân viên Chính thức mới được phép khai %s'% rec.holiday_status_id.name)

    # @api.constrains('project_id', 'holiday_status_id')
    # def check_has_project_w(self):
    #     for rec in self:
    #         if rec.holiday_status_id.code == 'W' and not rec.project_id:
    #             raise exceptions.ValidationError('Nghỉ phép Work from home phải có dự án')

    def action_draft(self):
        # if any(holiday.state not in ['confirm', 'refuse'] for holiday in self):
        #     raise UserError(_('Time off request state must be "Refused" or "To Approve" in order to be reset to draft.'))
        self.write({
            'state': 'draft',
            'first_approver_id': False,
            'second_approver_id': False,
        })
        linked_requests = self.mapped('linked_request_ids')
        if linked_requests:
            linked_requests.action_draft()
            linked_requests.unlink()
        timesheets = self.sudo().mapped('timesheet_ids')
        timesheets.write({'holiday_id': False})
        timesheets.unlink()
        self.activity_update()
        return True

    @api.depends('state', 'employee_id', 'department_id')
    def _compute_can_reset(self):
        super(HrLeave, self)._compute_can_reset()
        for holiday in self:
            if holiday.state in ['draft']:
                holiday.can_reset = False
                continue
            if self.env.user.has_group('hr.group_hr_manager'):
                holiday.can_reset = True
            elif holiday.state not in ['confirm', 'refuse']:
                holiday.can_reset = False

    def button_only_save(self):
        return

    @api.depends_context('uid')
    @api.depends('create_uid')
    def _compute_sent_ok(self):
        for rec in self:
            rec.sent_ok = not rec.create_uid or self.env.user == rec.create_uid

    # def _check_approval_update(self, state):
    #     """ Check if target state is achievable. """
    #     if self.env.is_superuser():
    #         return
    #
    #     current_employee = self.env.user.employee_id
    #     is_officer = self.env.user.has_group('hr_holidays.group_hr_holidays_user')
    #     is_manager = self.env.user.has_group('hr_holidays.group_hr_holidays_manager')
    #
    #     for holiday in self:
    #         val_type = holiday.validation_type
    #
    #         if state != 'confirm':
    #             if state == 'draft':
    #                 if holiday.state == 'refuse':
    #                     raise UserError('Chỉ người quản lý nghỉ phép mới có thể đặt lại nghỉ phép bị từ chối.')
    #                 if holiday.date_from and holiday.date_from.date() <= fields.Date.today():
    #                     raise UserError('Chỉ người quản lý nghỉ phép mới có thể đặt lại nghỉ phép đã bắt đầu.')
    #                 if holiday.employee_id != current_employee:
    #                     raise UserError('Chỉ người quản lý nghỉ phép mới có thể đặt lại nghỉ phép của người khác.')
    #             else:
    #                 if val_type == 'no_validation' and current_employee == holiday.employee_id:
    #                     continue
    #                 holiday.check_access_rule('write')
    #
    #                 if holiday.employee_id == current_employee:
    #                     raise UserError('Chỉ người quản lý nghỉ phép có thể phê duyệt/từ chối yêu cầu của chính mình.')
    #
    #                 leave_manager_ids = self.env['hr.employee'].sudo().search([('id', 'parent_of', holiday.employee_id.ids)]).mapped('user_id')
    #                 leave_manager_ids |= self.env['hr.employee'].sudo().search([('id', 'parent_of', holiday.employee_ids.ids)]).mapped('user_id')
    #                 if (state == 'validate1' and val_type == 'both') and holiday.holiday_type == 'employee':
    #                     if not is_officer and self.env.user not in leave_manager_ids:
    #                         raise UserError(_('Bạn phải là người quản lý của %s hoặc Người quản lý nghỉ để chấp thuận việc nghỉ phép này') % (holiday.employee_id.name))
    #
    #                 if (state == 'validate' and val_type == 'manager') and self.env.user not in leave_manager_ids:
    #                     if holiday.employee_id:
    #                         employees = holiday.employee_id
    #                     else:
    #                         employees = ', '.join(holiday.employee_ids.filtered(lambda e: self.env.user not in leave_manager_ids).mapped('name'))
    #                     raise UserError(_('You must be %s\'s Manager to approve this leave', employees))
    #
    #                 if not is_officer and (state == 'validate' and val_type == 'hr') and holiday.holiday_type == 'employee':
    #                     raise UserError('Bạn phải là người quản lý của %s hoặc Người quản lý nghỉ để chấp thuận việc nghỉ phép này')

    def activity_update(self):
        to_clean, to_do = self.env['hr.leave'], self.env['hr.leave']
        for holiday in self:
            note = _(
                'New %(leave_type)s Request created by %(user)s',
                leave_type=holiday.holiday_status_id.name,
                user=holiday.create_uid.name,
            )
            if holiday.state == 'draft':
                to_clean |= holiday
            elif holiday.state == 'confirm':
                holiday.with_context(mail_activity_quick_update=True).activity_schedule(
                    'hr_holidays.mail_act_leave_approval',
                    note=note,
                    user_id=holiday.sudo()._get_responsible_for_approval().id or self.env.user.id)
                message = f"Nhân viên {holiday.employee_id.name} đã trình lên bạn một đơn phê duyệt nghỉ phép: {holiday.number_of_days} ngày từ {holiday.request_date_from.strftime('%d/%m/%Y')}"
                holiday.with_context(hr_leave_email_cc=holiday.sudo().employee_id.department_id.manager_id.work_email).sudo().send_notify(message, holiday.sudo()._get_responsible_for_approval() or self.env.user, subject=f"Đơn nghỉ phép của {holiday.employee_id.name} cần được phê duyệt")
            elif holiday.state == 'validate1':
                holiday.activity_feedback(['hr_holidays.mail_act_leave_approval'])
                holiday.activity_schedule(
                    'hr_holidays.mail_act_leave_second_approval',
                    note=note,
                    user_id=holiday.sudo()._get_responsible_for_approval().id or self.env.user.id)
            elif holiday.state == 'validate':
                to_do |= holiday
            elif holiday.state == 'refuse':
                to_clean |= holiday
        if to_clean:
            to_clean.activity_unlink(['hr_holidays.mail_act_leave_approval', 'hr_holidays.mail_act_leave_second_approval'])
        if to_do:
            to_do.activity_feedback(['hr_holidays.mail_act_leave_approval', 'hr_holidays.mail_act_leave_second_approval'])

    # Override cho phép xóa ở trạng thái draft trong quá khứ
    @api.ondelete(at_uninstall=False)
    def _unlink_if_correct_states(self):
        error_message = _('You cannot delete a time off which is in %s state')
        state_description_values = {elem[0]: elem[1] for elem in self._fields['state']._description_selection(self.env)}
        now = fields.Datetime.now()

        if not self.env.user.has_group('hr_holidays.group_hr_holidays_user'):
            if any(hol.state not in ['draft', 'confirm'] for hol in self):
                raise UserError(error_message % state_description_values.get(self[:1].state))
            if any(hol.date_from < now for hol in self.filtered(lambda x: x.state != "draft")):
                raise UserError(_('You cannot delete a time off which is in the past'))
        else:
            for holiday in self.filtered(lambda holiday: holiday.state not in ['draft', 'cancel', 'confirm']):
                raise UserError(error_message % (state_description_values.get(holiday.state),))

class ProjectTask(models.Model):
    _inherit = 'project.task'
    _order = 'seq_id asc'

    en_remaining_hours = fields.Float(string='Số giờ dự kiến còn lại', compute='_compute_en_remaining_hours')

    @api.depends('en_handler')
    def _compute_en_remaining_hours(self):
        for rec in self:
            mh = sum([line.mh * line.workload for line in rec.en_task_position.wbs_version.resource_plan_id.order_line.filtered(lambda x: x.employee_id == rec.en_handler.employee_id)])
            planned = sum(self.env['project.task'].search([('en_task_position.wbs_version', '=', rec.en_task_position.wbs_version.id), ('id', '<', rec._origin.id), ('en_handler', '=', rec.en_handler.id)]).mapped('planned_hours'))
            rec.en_remaining_hours = mh - planned

    technical_field_selection = fields.Selection(related='stage_id.en_mark', string='🪙')
    date_deadline = fields.Date(copy=True)
    en_approver_id = fields.Many2one(string='Người xem xét', comodel_name='res.users', compute_sudo=True, compute='_compute_en_approver_id', store=True, readonly=False)

    @api.depends('project_id')
    def _compute_en_approver_id(self):
        for rec in self:
            rec.en_approver_id = rec.project_id.user_id

    a_ok = fields.Boolean(string='🚑', compute='_compute_en_ok')
    b_ok = fields.Boolean(string='🚑', compute='_compute_en_ok')
    c_ok = fields.Boolean(string='🚑', compute='_compute_en_ok')
    d_ok = fields.Boolean(string='🚑', compute='_compute_en_ok')
    e_ok = fields.Boolean(string='🚑', compute='_compute_en_ok')
    f_ok = fields.Boolean(string='🚑', compute='_compute_en_ok')

    @api.depends_context('uid')
    @api.depends('stage_id', 'en_handler', 'en_approver_id')
    def _compute_en_ok(self):
        for rec in self:
            rec.a_ok = rec.stage_id.en_mark in ['a', 'e']
            rec.b_ok = rec.stage_id.en_mark in ['a']
            rec.c_ok = rec.stage_id.en_mark in ['c', 'f'] and rec.en_handler == self.env.user
            rec.d_ok = rec.stage_id.en_mark not in ['e', 'g', 'b']
            rec.e_ok = rec.stage_id.en_mark in ['d', 'g'] and rec.en_approver_id == self.env.user
            rec.f_ok = rec.stage_id.en_mark in ['d'] and rec.en_approver_id == self.env.user

    decoration = fields.Char(compute='_compute_decoration')

    @api.depends('en_start_date', 'date_deadline')
    def _compute_decoration(self):
        for rec in self:
            decoration = False
            if rec.stage_id.en_mark not in ['b', 'g']:
                if rec.en_start_date and rec.date_deadline and rec.en_start_date <= fields.Date.Date.Date.context_today(rec) <= rec.date_deadline:
                    decoration = 'warning'
                if rec.date_deadline and fields.Date.Date.Date.context_today(rec) >= rec.date_deadline:
                    decoration = 'danger'
            rec.decoration = decoration

    def button_en_a(self):
        if not self.a_ok: raise exceptions.ValidationError('Không thỏa mãn điều kiện chuyển trạng thái. Không thể chuyển')
        self.write({'stage_id': self.env['project.task.type'].search([('en_mark', '=', 'c')], limit=1).id})
        if self.en_task_position.state == 'draft':
            en_task_position = self.en_task_position
            while en_task_position:
                en_task_position.write({'state': 'ongoing'})
                en_task_position = en_task_position.parent_id
        if self.en_task_position.project_stage_id.state == 'draft':
            self.en_task_position.project_stage_id.write({'state': 'ongoing'})

    def button_en_b(self):
        if not self.b_ok: raise exceptions.ValidationError('Không thỏa mãn điều kiện chuyển trạng thái. Không thể chuyển')
        self.write({'stage_id': self.env['project.task.type'].search([('en_mark', '=', 'b')], limit=1).id})

    def button_en_c(self):
        if not self.c_ok: raise exceptions.ValidationError('Không thỏa mãn điều kiện chuyển trạng thái. Không thể chuyển')
        if self.en_approver_id:
            self.send_notify('Bạn có thông tin cần xem xét', self.en_approver_id)
        self.write({'stage_id': self.env['project.task.type'].search([('en_mark', '=', 'd')], limit=1).id})

    def button_en_d(self):
        if not self.d_ok: raise exceptions.ValidationError('Không thỏa mãn điều kiện chuyển trạng thái. Không thể chuyển')
        self.write({'stage_id': self.env['project.task.type'].search([('en_mark', '=', 'e')], limit=1).id})

    def button_en_e(self):
        if not self.e_ok: raise exceptions.ValidationError('Không thỏa mãn điều kiện chuyển trạng thái. Không thể chuyển')
        self.write({'stage_id': self.env['project.task.type'].search([('en_mark', '=', 'f')], limit=1).id})

    def button_en_f(self):
        if not self.f_ok: raise exceptions.ValidationError('Không thỏa mãn điều kiện chuyển trạng thái. Không thể chuyển')
        self.write({'stage_id': self.env['project.task.type'].search([('en_mark', '=', 'g')], limit=1).id})

    @api.constrains('en_start_date', 'date_deadline', 'en_task_position', 'en_handler', 'planned_hours')
    def _en_constrains_start_deadline_date(self):
        if self._context.get('skip_constrains_start_deadline_date'):
            return
        lg = self.env['res.lang']._lang_get(self.env.user.lang) or get_lang(self.env)

        error_date_in_task = self.filtered(lambda rec: rec.en_start_date and rec.date_deadline and rec.en_start_date > rec.date_deadline)
        if error_date_in_task:
            lst = [f'\t- {p.name} thuộc về gói việc {p.en_task_position.name}' for p in error_date_in_task]
            raise exceptions.ValidationError("Ngày bắt đầu nhiệm vụ phải nhỏ hơn ngày kết thúc nhiệm vụ. Nhiệm vụ lỗi gồm:\n" + '\n'.join(lst))

        need_checks = self.filtered(lambda rec: rec.en_task_position and rec.en_start_date and rec.date_deadline and rec.en_handler)
        error_date_start = need_checks.filtered(lambda rec: not (rec.en_task_position.date_start <= rec.en_start_date <= rec.date_deadline))
        if error_date_start:
            lst = [f'\t- {p.name} - {p.en_task_position.wp_code}: {p.en_task_position.name}' for p in error_date_start]
            raise exceptions.ValidationError("Ngày bắt đầu công việc không được  nhỏ hơn ngày bắt đầu gói việc của nó. Cặp công việc - gói việc lỗi gồm:\n" + '\n'.join(lst))
        error_date_end = need_checks.filtered(lambda rec: not (rec.en_start_date <= rec.date_deadline <= rec.en_task_position.date_end))
        if error_date_end:
            lst = [f'\t- {p.name} - {p.en_task_position.wp_code}: {p.en_task_position.name}' for p in error_date_end]
            raise exceptions.ValidationError("Ngày kết thúc công việc không được lớn hơn ngày kết thúc gói việc của nó. Cặp công việc - gói việc lỗi gồm:\n" + '\n'.join(lst))
        # for task in need_checks:
        #     wbs = task.en_wbs_id
        #     hours_total = wbs.resource_plan_id.hours_total
        #     hours_task = sum(wbs.en_wbs_task_ids.filtered(lambda t: t.stage_id.en_mark != 'b').mapped('planned_hours'))
        #     if hours_task > hours_total:
        #         raise exceptions.ValidationError(f'Tổng của số dự kiến trong các công việc ({hours_task}) không được lớn hơn Tổng nguồn lực (MH) của KHNL ({hours_total})')

        # error_resource_plan = need_checks
        # for rec in need_checks:
        #     for line in rec.en_task_position.wbs_version.resource_plan_id.order_line.filtered(lambda x: x.employee_id.user_id == rec.en_handler):
        #         if line.date_start <= rec.en_start_date <= line.date_end and line.date_start <= rec.date_deadline <= line.date_end:
        #             error_resource_plan -= rec
        #             break
        # if error_resource_plan:
        #     lst = [f'\t- {p.name}' for p in error_resource_plan]
        #     raise exceptions.ValidationError("Nhiệm vụ được tạo phải nằm trong khoảng sử dụng nguồn lực. Nhiệm vụ lỗi gồm:\n" + '\n'.join(lst))

        # error_workload = {}
        # for rec in need_checks:
        #     dated_txt = []
        #     for li in rec.en_task_position.wbs_version.resource_plan_id.order_line.filtered(lambda x: x.employee_id.user_id == rec.en_handler):
        #         if li.date_start <= rec.en_start_date <= li.date_end and li.date_start <= rec.date_deadline <= li.date_end:
        #             tasks = self.env['project.task'].search([('id', '!=', rec.id), ('en_handler', '=', rec.en_handler.id), ('en_task_position.wbs_version', '=', rec.en_task_position.wbs_version.id),
        #                                                      ('en_start_date', '!=', False), ('date_deadline', '!=', False),
        #                                                      '|',
        #                                                      '&', ('en_start_date', '<=', li.date_start), ('date_deadline', '>=', li.date_start),
        #                                                      '&', ('en_start_date', '>=', li.date_start), ('en_start_date', '<=', li.date_end),
        #                                                      ], order='date_deadline desc')
        #             mh = li.mh * li.workload
        #             if rec.planned_hours + sum(tasks.mapped("planned_hours")) > mh:
        #                 for line in rec.en_task_position.wbs_version.resource_plan_id.order_line.filtered(lambda x: x.employee_id.user_id == rec.en_handler):
        #                     line_tasks = self.env['project.task'].search([('id', 'not in', self.ids), ('en_handler', '=', rec.en_handler.id), ('en_task_position.wbs_version', '=', rec.en_task_position.wbs_version.id),
        #                                                                   ('en_start_date', '!=', False), ('date_deadline', '!=', False),
        #                                                                   '|',
        #                                                                   '&', ('en_start_date', '<=', line.date_start), ('date_deadline', '>=', line.date_start),
        #                                                                   '&', ('en_start_date', '>=', line.date_start), ('en_start_date', '<=', line.date_end),
        #                                                                   ], order='date_deadline desc')
        #                     dated_txt += [f'{line.mh * line.workload - sum(line_tasks.mapped("planned_hours"))}h từ {line.date_start.strftime(lg.date_format)} → {line.date_end.strftime(lg.date_format)}']
        #     if dated_txt:
        #         error_workload[rec.id] = dated_txt
        # if error_workload:
        #     task_error = []
        #     workload_error = []
        #     for task_id in error_workload:
        #         task = self.env['project.task'].browse(task_id)
        #         task_error.append(f'\t- {task.name} của {task.en_handler.display_name}')
        #         workload_error.append(f'\t- {task.en_handler.display_name} còn ' + ' hoặc '.join(error_workload[task_id]))
        #     raise exceptions.ValidationError(f"Số giờ trong nhiệm vụ đã vượt quá số giờ có thể sử dụng.\n Nhiệm vụ lỗi gồm:\n%s\nSố giờ còn có thể sử dụng của nguồn lực là:\n%s"%('\n'.join(task_error), '\n'.join(workload_error)))

    # @api.returns('self', lambda value: value.id)
    # def copy(self, default=None):
    #     res = super().copy(default)
    #     self.timesheet_ids.filtered(lambda x: x.en_state != 'approved').write({'task_id': res.id})
    #     return res

    wbs_state = fields.Selection(related='en_task_position.wbs_version.state')

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super().fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if view_type != 'form':
            return res
        doc = etree.XML(res['arch'])
        for node in doc.xpath(f"//{view_type}"):
            wbs_state = etree.Element('field', {'name': 'wbs_state', 'modifiers': json.dumps({'column_invisible': True, 'invisible': True})})
            node.append(wbs_state)
        for node in doc.xpath("//field"):
            if self.env['project.task'].fields_get([node.attrib.get('name')]).get(node.attrib.get('name'), {}).get('readonly'): continue
            if node.attrib.get('name') in ['timesheet_ids', 'stage_id', 'en_progress', 'en_task_position']: continue
            modifiers = json.loads(node.get("modifiers", "{}"))
            readonly = modifiers.get('readonly', [])
            # readonly_domain = [('wbs_state', '=', 'approved')]
            # if readonly and isinstance(readonly, list):
            #     readonly_domain = Domain.OR([readonly, readonly_domain])
            # elif not readonly and isinstance(readonly, bool):
            #     readonly_domain = readonly
            # modifiers['readonly'] = readonly_domain
            # node.set("modifiers", json.dumps(modifiers)) # tạm thời bỏ readonly
        res['arch'] = etree.tostring(doc, encoding='unicode')
        return res

    technical_field_27058 = fields.Float(string='🚑', compute_sudo=True, compute='_compute_technical_field_27058')

    @api.depends('en_start_date', 'date_deadline')
    def _compute_technical_field_27058(self):
        for rec in self:
            technical_field_27058 = 0
            employee = rec.en_handler.employee_id or self.env.user.employee_id
            if rec.en_start_date and rec.date_deadline and employee:
                if rec.en_start_date > fields.Date.today() or rec.stage_id.en_mark == 'b':
                    technical_field_27058 = 0
                elif rec.date_deadline <= fields.Date.today():
                    technical_field_27058 = 1
                else:
                    workmonth_hours = self.env['en.technical.model'].convert_daterange_to_count(employee, rec.en_start_date, rec.date_deadline, exclude_tech_type=['off', 'holiday', 'not_work', 'layoff'])
                    workperiod_hours = self.env['en.technical.model'].convert_daterange_to_count(employee, rec.en_start_date, fields.Date.today(), exclude_tech_type=['off', 'holiday', 'not_work', 'layoff'])

                    if workmonth_hours:
                        technical_field_27058 = workperiod_hours / workmonth_hours
            rec.technical_field_27058 = min(technical_field_27058, 1)

    parent_id = fields.Many2one(tracking=True)

    @api.depends('timesheet_ids.ot_time', 'timesheet_ids.en_state', 'timesheet_ids.ot_state', 'timesheet_ids.unit_amount')
    def _compute_effective_hours(self):
        for rec in self:
            effective_hours = 0
            effective_hours += sum(rec.timesheet_ids.filtered(lambda x: x.en_state in ['approved', 'waiting']).mapped('unit_amount'))
            effective_hours += sum(rec.timesheet_ids.filtered(lambda x: x.ot_state == 'approved').mapped('ot_time'))
            rec.effective_hours = effective_hours

    technical_field_27026 = fields.Many2many(string='🐧', comodel_name='res.users', compute_sudo=True, compute='_compute_technical_field_27026')

    @api.depends('en_task_position')
    def _compute_technical_field_27026(self):
        for rec in self:
            rec.technical_field_27026 = rec.project_id.en_resource_project_ids.mapped('employee_id.user_id')

    en_task_position = fields.Many2one(string='Gói công việc', comodel_name='en.workpackage', ondelete='cascade', required=True, tracking=True, domain="[('id','in',en_task_position_ids)]")
    en_wbs_id = fields.Many2one(related='en_task_position.wbs_version', store=True)
    en_wbs_old_id = fields.Many2one('en.wbs', 'Phiên bản wbs cũ', copy=False)
    en_wbs_state = fields.Selection(related='en_task_position.wbs_version.state', store=True)
    en_requester = fields.Many2one(string='Người yêu cầu', comodel_name='res.users', required=True, default=lambda self: self.env.user)
    en_supervisor = fields.Many2one(string='Người giám sát', comodel_name='res.users')

    technical_field_27450 = fields.Many2many(string='🪙', comodel_name='res.users', compute_sudo=True, compute='_compute_technical_field_27450')

    en_task_position_ids = fields.Many2many('en.workpackage', 'Các gói công việc', compute='_compute_en_task_position_ids')

    @api.onchange('en_task_position')
    def _onchange_en_task_position(self):
        for rec in self:
            if rec.project_id.user_id == self.env.user or self.env.user in rec.project_id.en_project_vicepm_ids: continue
            if rec.en_task_position and rec.en_task_position.user_id.id != self.env.uid:
                raise ValidationError('Bạn không thể tạo công việc cho gói việc mà bạn không phải là người chịu trách nhiệm')

    @api.depends('project_id')
    def _compute_en_task_position_ids(self):
        for rec in self:
            rec.en_task_position_ids = self.env['en.workpackage'].search([('project_id', '=', rec.project_id.id), ('wbs_state', '=', 'approved'), ('child_ids', '=', False)]).ids

    @api.depends('en_task_position')
    def _compute_technical_field_27450(self):
        for rec in self:
            rec.technical_field_27450 = rec.project_id.en_resource_project_ids.mapped('employee_id.user_id')

    en_handler = fields.Many2one(string='Người chịu trách nhiệm', comodel_name='res.users', required=False, tracking=True)
    en_task_code = fields.Char(string='Mã công việc', readonly=True, copy=False, compute_sudo=True, compute='_compute_en_task_code', store=True)
    seq_id = fields.Integer(string='💰', default=lambda self: int(self.env['ir.sequence'].next_by_code('seq.id')), copy=False)
    origin_code = fields.Char(string='Mã gốc', readonly=True, copy=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('en_supervisor'):
                vals['en_supervisor'] = vals.get('en_requester')
            if vals.get('en_handler'):
                vals['user_ids'] = [(6, 0, [vals.get('en_handler')])]
            # if vals.get('origin_code'):
            #     old_tasks = self.env['project.task'].search([('origin_code', '=', vals.get('origin_code'))])
            #     vals['timesheet_ids'] = [(6, 0, old_tasks.mapped('timesheet_ids').filtered(lambda x: x.en_state != 'approved').ids)]
        res = super().create(vals_list)
        for rec in res:
            if not rec.origin_code:
                rec.write({'origin_code': f'T{rec.id}'})
        return res

    def write(self, vals):
        if vals.get('stage_id') and self.stage_id.en_mark == 'g':
            vals['en_progress'] = 0
        if vals.get('stage_id') and self.env['project.task.type'].browse(int(vals.get('stage_id'))).en_mark == 'g':
            vals['en_progress'] = 1
        if vals.get('en_handler'):
            vals['user_ids'] = [(6, 0, [vals.get('en_handler')])]
        if "en_progress" in vals:
            return super(ProjectTask, self.with_context(skip_timesheet_notify=True)).write(vals)
        res = super().write(vals)
        return res

    @api.depends("project_id", "seq_id")
    def _compute_en_task_code(self):
        for rec in self:
            sequence = 1
            lasted_task = self.sudo().search([('project_id', '=', rec.project_id.id), ('seq_id', '<', rec.seq_id)], order='seq_id desc', limit=1)
            if lasted_task.en_task_code:
                sequence = int(lasted_task.en_task_code.replace('T.', '')) + 1
            rec.en_task_code = f"T.{sequence}"

    en_start_date = fields.Date(string='Ngày bắt đầu', required=True)
    en_progress = fields.Float(string='% Hoàn thành', default=0, required=True, tracking=True)
    en_open_date = fields.Datetime(string='Ngày bắt đầu thực tế', compute_sudo=True, compute='_compute_en_open_date', store=True, readonly=False, copy=False) # tạm thời bỏ readonly

    @api.constrains('en_progress')
    def _constrains_en_progress(self):
        for rec in self:
            if rec.en_progress < 0 or rec.en_progress > 1:
                raise ValidationError('% Hoàn thành chỉ được nhập trong khoảng 0 -> 100')

    @api.depends('stage_id')
    def _compute_en_open_date(self):
        for rec in self:
            en_open_date = rec.en_open_date
            if not en_open_date and rec.stage_id.en_mark == 'c':
                en_open_date = fields.Datetime.now()
            rec.en_open_date = en_open_date

    en_close_date = fields.Datetime(string='Ngày kết thúc thực tế', compute_sudo=True, compute='_compute_en_close_date', store=True, readonly=False, copy=False) # tạm thời bỏ readonly

    @api.depends('stage_id')
    def _compute_en_close_date(self):
        for rec in self:
            en_close_date = rec.en_close_date
            if rec.stage_id.en_mark == 'g':
                en_close_date = fields.Datetime.now()
            rec.en_close_date = en_close_date

    en_real_time = fields.Float(string='Giờ thực tế (h)', compute_sudo=True, compute='_compute_en_real_time', store=True)

    @api.depends('en_open_date', 'en_close_date')
    def _compute_en_real_time(self):
        for rec in self:
            en_real_time = 0
            if not rec.en_open_date or not rec.en_close_date:
                rec.en_real_time = en_real_time
                continue
            en_real_time = (max([rec.en_close_date, rec.en_open_date]) - min([rec.en_close_date, rec.en_open_date])).total_seconds() / 3600
            if rec.en_open_date > rec.en_close_date:
                en_real_time = -1 * en_real_time
            rec.en_real_time = en_real_time

    planned_hours = fields.Float(compute='_compute_planned_hours', store=True, readonly=False)
    max_planned_hours = fields.Float(string='Số giờ tối đa', compute='_compute_max_planned_hours')

    resource_planning_id = fields.Many2one(related='project_id.en_resource_id')

    crm_lead_id = fields.Many2one('crm.lead', 'Cơ hội', domain="['|', '|', '|', ('stage_id.name', 'ilike', 'Mới'), ('stage_id.name', 'ilike', 'Đã thẩm định'), ('stage_id.name', 'ilike', 'Đề xuất'), ('stage_id.name', 'ilike', 'Thương thảo HĐ')]")
    project_presale = fields.Boolean('Presale', compute='_compute_presale')

    @api.depends('project_id.en_project_type_id', 'project_id.en_project_type_id.is_presale', 'project_id')
    def _compute_presale(self):
        for rec in self:
            rec.project_presale = False
            if rec.project_id.en_project_type_id and rec.project_id.en_project_type_id.is_presale:
                rec.project_presale = True

    is_pm_crm = fields.Boolean(compute='_compute_pm_crm')

    @api.depends('en_task_position', 'en_task_position.user_id')
    def _compute_pm_crm(self):
        for rec in self:
            rec.is_pm_crm = False
            if rec.en_task_position.user_id and rec.en_task_position.user_id.id == self.env.uid:
                rec.is_pm_crm = True

    # @api.constrains('en_task_position', 'en_start_date')
    # def _en_constrains_en_start_date(self):
    #     if any(rec.en_task_position and rec.en_start_date and rec.en_start_date < rec.en_task_position.date_start for rec in self):
    #         raise exceptions.ValidationError(f'Ngày bắt đầu của công việc ≥ Ngày bắt đầu của gói công việc')

    # @api.constrains('planned_hours')
    # def _en_constrains_planned_hours(self):
    #     for rec in self:
    #         if rec.max_planned_hours and rec.planned_hours > rec.max_planned_hours:
    #             raise exceptions.ValidationError(f'Gói việc {rec.en_task_position.display_name} có nhiệm vụ bị quá thời lượng tối đa 8h/ngày. Vui lòng kiểm tra và sửa lại thời gian nhiệm vụ.')

    @api.depends('en_start_date', 'date_deadline', 'en_handler')
    def _compute_max_planned_hours(self):
        for rec in self:
            max_planned_hours = 0
            if not rec.en_start_date or not rec.date_deadline:
                rec.max_planned_hours = max_planned_hours
                continue
            max_planned_hours = (max([rec.en_start_date, rec.date_deadline]) - min([rec.en_start_date, rec.date_deadline])).total_seconds() / 86400 * (rec.en_handler.employee_id.resource_calendar_id.hours_per_day or 8)
            rec.max_planned_hours = max_planned_hours + (rec.en_handler.employee_id.resource_calendar_id.hours_per_day or 8)

    # @api.onchange('en_start_date', 'date_deadline')
    # def en_onchange_start_deadline(self):
    #     if self.en_start_date and self.date_deadline and self.en_start_date > self.date_deadline:
    #         return {'warning': {
    #             'title': 'Lỗi xác nhận',
    #             'message': 'Ngày kết thúc không thể nhỏ hơn ngày bắt đầu',
    #         }}

    # @api.onchange('planned_hours')
    # def en_onchange_planned_hours(self):
    #     if self.planned_hours > 40:
    #         return {'warning': {
    #             'title': 'Lỗi xác nhận',
    #             'message': 'Số giờ dự kiến cho một công việc không được vượt quá 40h',
    #         }}

    # @api.constrains('planned_hours')
    # def en_constrains_planned_hours(self):
    #     if any(rec.planned_hours > 40 for rec in self):
    #         raise exceptions.ValidationError('Số giờ dự kiến cho một công việc không được vượt quá 40h')

    @api.depends('en_start_date', 'date_deadline', 'en_handler')
    def _compute_planned_hours(self):
        for rec in self:
            planned_hours = rec.planned_hours
            if not rec.en_start_date or not rec.date_deadline:
                rec.planned_hours = planned_hours
                continue
            if rec.en_start_date > rec.date_deadline:
                rec.planned_hours = planned_hours
                continue
            user_id = rec.en_handler
            employee = user_id.employee_id
            if not employee:
                rec.planned_hours = planned_hours
                continue
            datetime_start = datetime.combine(rec.en_start_date, time.min)
            datetime_end = datetime.combine(rec.date_deadline, time.max)
            planned_hours = self.env['en.technical.model'].convert_daterange_to_hours(employee, datetime_start, datetime_end)
            rec.planned_hours = planned_hours

    @api.model
    def _task_message_auto_subscribe_notify(self, users_per_task):
        if not self or self.env.context.get('mail_auto_subscribe_no_notify'):
            return
        return super(ProjectTask, self)._task_message_auto_subscribe_notify(users_per_task=users_per_task)

    def unlink(self):
        return super().unlink()

    related_task_id = fields.Many2one('project.task', readonly=1, copy=False)
    project_id = fields.Many2one('project.project', string='Project',
                                 compute='_compute_project_id', recursive=True, store=True, readonly=False,
                                 index=True, tracking=True, check_company=True, change_default=True)

    @api.depends('parent_id.project_id', 'en_task_position.project_id')
    def _compute_project_id(self):
        for task in self:
            if task.en_task_position and task.en_task_position.project_id:
                task.project_id = task.en_task_position.project_id
            elif task.parent_id and task.parent_id.project_id:
                task.project_id = task.parent_id.project_id

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        if self._context.get('import_file') and self._context.get('import_order_line') == 'wbs_version.id' and self._context.get(
                'relation_id'):
            args = args or []
            args = [('wbs_version', '=', self._context.get('relation_id'))] + args
        return super()._name_search(name, args, operator, limit, name_get_uid)


class ProjectTaskType(models.Model):
    _inherit = 'project.task.type'

    en_mark = fields.Selection(string='Giai đoạn nhiệm  vụ', selection=[('a', 'Chờ thực hiện'),
                                                                        ('b', 'Hủy bỏ'),
                                                                        ('c', 'Đang thực hiện'),
                                                                        ('d', 'Chờ xem xét'),
                                                                        ('e', 'Bị trì hoãn'),
                                                                        ('f', 'Làm lại'),
                                                                        ('g', 'Hoàn thành')
                                                                        ], required=True)

    @api.constrains('en_mark')
    def _en_constrains_en_mark(self):
        if any(self.search_count([('en_mark', '=', rec.en_mark)]) > 1 for rec in self):
            raise exceptions.ValidationError('Đã tồn tại Giai đoạn nhiệm vụ này!')


class AccountAnalyticLineConfirm(models.TransientModel):
    _name = 'account.analytic.line.confirm.wizard'
    _description = 'Xác nhận'

    def do(self):
        for rec in self.env[self._context.get('active_model')].browse(self._context.get('active_ids')):
            rec.en_button_sent()
        return {'type': 'ir.actions.act_window_close'}


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    request_date = fields.Datetime("Thời gian gửi phê duyệt", readonly=True, copy=False)
    approver = fields.Char(string='Người phê duyệt', size=32, required=False, readonly=True, copy=False)
    approve_date = fields.Datetime("Thời gian phê duyệt", readonly=True, copy=False)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        res = super(AccountAnalyticLine, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
        if groupby == ['en_state']:
            map_state = {
                'new': 0,
                'sent': 1,
                'approved': 2,
                'waiting': 3,
                'cancel': 4,
            }
            return sorted(res, key=lambda l: map_state.get(l.get('en_state'), 10))
        return res

    def button_en_copy(self):
        return self.copy({'date': fields.Date.today(), 'ot_id': False})

    project_department_id = fields.Many2one('hr.department', compute='_compute_project_department', string='Trung tâm theo dự án', store=True)

    @api.depends('project_id', 'project_id.en_department_id')
    def _compute_project_department(self):
        for rec in self:
            if rec.project_id.en_department_id:
                rec.project_department_id = rec.project_id.en_department_id
            else:
                rec.project_department_id = False

    mh = fields.Float(string='Manhour', compute_sudo=True, compute='_compute_m_uom')
    md = fields.Float(string='Manday', compute_sudo=True, compute='_compute_m_uom')
    mm = fields.Float(string='Manmonth', compute_sudo=True, compute='_compute_m_uom')

    @api.depends('employee_id', 'date', 'unit_amount', 'ot_id', 'ot_id.state', 'ot_id.time')
    def _compute_m_uom(self):
        todate = fields.Date.today()

        for rec in self:
            mm = 0
            md = 0
            mh = 0
            if not rec.employee_id or not rec.date:
                rec.mm = mm
                rec.md = md
                rec.mh = mh
                continue
            employee = rec.employee_id
            date_step = rec.date
            compared_from = date_step + relativedelta(day=1)
            compared_to = date_step + relativedelta(months=1, day=1, days=-1)
            y = 0
            tech_data = self.env['en.technical.model'].convert_daterange_to_data(employee, datetime.combine(compared_from, time.min), datetime.combine(compared_to, time.max))
            for d in tech_data:
                tech = tech_data.get(d)
                y += tech.get('number') / 8
            x = rec.unit_amount
            if rec.ot_id.state == 'approved':
                x += rec.ot_id.time
            mm += x / 8 / y if y else 0
            md += x / 8
            mh += x
            rec.mm = mm
            rec.md = md
            rec.mh = mh

    def en_false_button_sent(self):
        if self.en_state != 'new': return
        if not self.en_sent_ok: return

        return {
            'name': 'Xác nhận',
            'view_mode': 'form',
            'target': 'new',
            'res_model': 'account.analytic.line.confirm.wizard',
            'type': 'ir.actions.act_window',
            'context': {'active_id': self[0].id, 'active_ids': self.ids, 'active_model': self._name},
        }

    def button_confirm_approve(self):
        return {
            'name': 'Xác nhận',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'message.popup.confirm',
            'context': {
                'default_master_id': self._name + ',' + str(self.id),
                'default_func': 'en_button_approved',
                'default_message': 'Duyệt yêu cầu, tiếp tục?'
            },
            'target': 'new',
            'view_id': False
        }

    def button_confirm_reject(self):
        return {
            'name': 'Xác nhận',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'message.popup.confirm',
            'context': {
                'default_master_id': self._name + ',' + str(self.id),
                'default_func': 'en_button_cancel',
                'default_message': 'Từ chối yêu cầu, tiếp tục?'
            },
            'target': 'new',
            'view_id': False
        }

    def en_button_sent(self):
        if self.en_state != 'new': return
        if not self.en_sent_ok: return
        if self.project_id and not self.env['en.resource.detail'].search_count([('employee_id', '=', self.employee_id.id), ('date_start', '<=', self.date), ('date_end', '>=', self.date), ('order_id', '=', self.project_id.en_resource_id.id)]):
            raise UserError('Timesheet bạn vừa khai báo nằm ngoài thời gian làm việc của bạn trong Kế hoạch nguồn lực. Vui lòng liên hệ PM để được xử lý.')
        self.en_state = 'sent'
        self.ot_id.button_sent()
        self.request_date = fields.Datetime.now()

    def en_button_approved(self):
        if self.en_state != 'sent': return
        if not self.en_approve_ok: return
        self.sudo().write(dict(en_state = 'approved'))
        self.sudo().approver = self.env.user.employee_id.name
        self.sudo().approve_date = fields.Datetime.now()

    def en_button_cancel(self):
        if self.en_state != 'sent': return
        if not self.en_approve_ok: return
        self.sudo().write(dict(en_state = 'cancel'))
        self.sudo().approver = self.env.user.employee_id.name
        self.sudo().approve_date = fields.Datetime.now()

    def en_button_waiting(self):
        if self.en_state != 'approved': return
        if not self.en_sent_ok: return
        self.en_state = 'waiting'

    def en_button_cancel2(self):
        if self.en_state != 'waiting': return
        if not self.en_approve_ok: return
        self.sudo().en_state = 'cancel'
        self.sudo().approver = self.env.user.employee_id.name
        self.sudo().approve_date = fields.Datetime.now()

    def en_button_cancel_cancel(self):
        if self.en_state != 'waiting': return
        self.sudo().en_state = 'approved'
        self.sudo().approver = self.env.user.employee_id.name
        self.sudo().approve_date = fields.Datetime.now()

    def en_create_over_time(self):
        name = 'Xem Tăng ca'
        if not self.ot_id:
            name = 'Tạo mới Tăng ca'
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': 'en.hr.overtime',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_id': self.id,
                'default_task_id': self.task_id.id,
                'default_timesheet_ids': [(6, 0, self.ids)],
                'default_date_from': self.date,
                'default_date_to':  self.date,
            },
            'views': [[False, 'form']],
            'res_id': self.ot_id.id
        }

    def en_create_over_time_nonproject(self):
        name = 'Xem Tăng ca'
        if not self.ot_id:
            name = 'Tạo mới Tăng ca'
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': 'en.hr.overtime',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_id': self.id,
                'default_en_nonproject_task_id': self.en_nonproject_task_id.id,
                'default_timesheet_ids': [(6, 0, self.ids)],
                'default_date_from': self.date,
                'default_date_to':  self.date,
            },
            'views': [[False, 'form']],
            'res_id': self.ot_id.id
        }

    ot_time = fields.Float('Số giờ OT', related='ot_id.time', store=True)
    ot_state = fields.Selection(string='Trạng thái OT', related='ot_id.state', store=True)
    ot_date_from = fields.Datetime('Bắt đầu OT', related='ot_id.date_from')
    ot_date_to = fields.Datetime('Kết thúc OT', related='ot_id.date_to')

    en_sent_ok = fields.Boolean(string='💰', compute='_compute_en_sent_ok')

    @api.depends_context('uid')
    @api.depends('employee_id')
    def _compute_en_sent_ok(self):
        for rec in self:
            rec.en_sent_ok = rec.employee_id == self.env.user.employee_id

    en_approve_ok = fields.Boolean(string='💰', compute='_compute_en_approve_ok')

    @api.depends_context('uid')
    @api.depends('en_approver_id')
    def _compute_en_approve_ok(self):
        for rec in self:
            rec.en_approve_ok = rec.en_approver_id == self.env.user

    def unlink(self):
        if any(rec.en_state == 'approved' for rec in self):
            raise exceptions.ValidationError('Timesheet đã phê duyệt không thể xóa')
        if any(rec.en_state != 'new' for rec in self):
            raise exceptions.ValidationError('Không thể xóa timesheet')
        return super().unlink()

    en_state = fields.Selection(string='Trạng thái', selection=[('new', 'Mới'), ('sent', 'Chờ phê duyệt'), ('approved', 'Đã phê duyệt'), ('waiting', 'Chờ hủy duyệt'), ('cancel', 'Hủy')], default='new', readonly=True, copy=False, required=True)
    en_approver_id = fields.Many2one(string='Người phê duyệt', comodel_name='res.users', compute_sudo=True, compute='_compute_en_approver_id', store=True, readonly=False)

    @api.depends('task_id', 'task_id.project_id.user_id', 'en_nonproject_task_id', 'en_nonproject_task_id.en_supervisor_id', 'task_id.project_id.en_project_type_id', 'task_id.en_task_position', 'task_id.en_task_position.user_id')
    def _compute_en_approver_id(self):
        for rec in self:
            en_approver_id = False
            if not rec.task_id.project_id.en_project_type_id.is_presale and rec.task_id.project_id.user_id:
                en_approver_id = rec.task_id.project_id.user_id
            if rec.task_id.project_id.en_project_type_id.is_presale and rec.task_id.en_task_position.user_id:
                en_approver_id = rec.task_id.en_task_position.user_id
            if rec.en_nonproject_task_id.en_supervisor_id:
                en_approver_id = rec.en_nonproject_task_id.en_supervisor_id
            rec.en_approver_id = en_approver_id

    name = fields.Char(required=True)

    @api.constrains('unit_amount', 'employee_id', 'date', 'en_state')
    def _en_constrains_unit_amount(self):
        for rec in self:
            if rec.global_leave_id:
                continue
            if rec.date > fields.Date.Date.Date.context_today(self) and not rec.holiday_id:
                raise exceptions.ValidationError('Không được khai timesheet trong tương lai.')
            amount = sum(self.search([('employee_id', '=', rec.employee_id.id), ('date', '=', rec.date),
                                      ('en_state', '!=', 'cancel'), ('en_state', '!=', 'new')]).mapped('unit_amount'))

            # check time trong phần nghỉ phép
            leaves = self.env['hr.leave'].search([
                ('employee_id', '=', rec.employee_id.id),
                ('state', 'in', ['confirm', 'validate1', 'validate']),
                ('holiday_status_id.code', '!=', 'W'),
                ('date_from', '>=', rec.date), ('date_to', '<=', rec.date)
            ])
            for leave in leaves:
                amount += leave.number_of_hours_display

            if amount < 0 or amount > 8:
                raise exceptions.ValidationError(f'Tổng số giờ khai Timesheet ngày {rec.date.strftime("%d/%m/%Y")} không thể quá 8h')

    @api.constrains('date')
    def _constrains_date_add_ts(self):
        for rec in self:
            if rec.task_id:
                if rec.task_id.date_deadline and rec.date > rec.task_id.date_deadline:
                    raise exceptions.ValidationError('Không được khai Timesheet vào ngày vượt quá hạn hoàn thành của task.')
                if rec.task_id.en_start_date and rec.date < rec.task_id.en_start_date:
                    raise exceptions.ValidationError('Không được khai Timesheet vào ngày trước ngày bắt đầu của task.')

            if rec.en_nonproject_task_id:
                if rec.en_nonproject_task_id.en_end_date and rec.date > rec.en_nonproject_task_id.en_end_date:
                    raise ValidationError('Không được khai Timesheet vào ngày vượt quá hạn hoàn thành của task.')
                if rec.en_nonproject_task_id.en_start_date and rec.date < rec.en_nonproject_task_id.en_start_date:
                    raise ValidationError('Không được khai Timesheet vào ngày trước ngày bắt đầu của task.')

    unit_amount_holiday = fields.Float('Số giờ nghỉ phép', compute='_get_unit_amount_holiday')

    @api.depends('unit_amount', 'holiday_id')
    def _get_unit_amount_holiday(self):
        for rec in self:
            rec.unit_amount_holiday = rec.unit_amount if rec.holiday_id or rec.global_leave_id else 0

    @api.constrains('ot_id')
    def _en_constrains_ot_id(self):
        for rec in self:
            if rec.ot_id and self.search_count([('ot_id', '=', rec.ot_id.id)]) > 1:
                raise exceptions.ValidationError('Thông tin Làm thêm này đã được ghi nhận tại timesheet khác')

    ot_id = fields.Many2one(string='Làm thêm', comodel_name='en.hr.overtime')
    employee_id = fields.Many2one(index=True)
    date = fields.Date(index=True)
    en_total_amount = fields.Float(string='Tổng số giờ', compute_sudo=True, compute='_compute_en_total_amount', store=True)

    @api.depends('unit_amount', 'ot_id.time', 'ot_id.state')
    def _compute_en_total_amount(self):
        for rec in self:
            rec.en_total_amount = rec.unit_amount + rec.ot_id.time if rec.ot_id.state == 'approved' else rec.unit_amount

    technical_field_27607_1 = fields.Char(string='🚑', compute='_compute_technical_field_27607_1', store=True)
    project_code = fields.Char(related='project_id.en_code')

    @api.constrains('date', 'unit_amount', 'global_leave_id')
    def _check_date_holiday(self):
        for rec in self:
            if self._context.get('no_constrains', False):
                continue
            if rec.date and rec.unit_amount > 0 and not rec.global_leave_id:
                holiday = self.env['resource.calendar.leaves'].search([('is_holiday', '=', True), ('date_from_convert', '<=', rec.date), ('date_to_convert', '>=', rec.date)])
                if holiday:
                    raise UserError('Bạn không được khai TS vào ngày lễ')

    @api.depends('date')
    def _compute_technical_field_27607_1(self):
        for rec in self:
            rec.technical_field_27607_1 = rec.date.strftime("%d/%m/%Y") if rec.date else ''

    technical_field_27607_2 = fields.Char(string='🚑', compute='_compute_technical_field_27607_2', store=True)

    @api.depends('en_state')
    def _compute_technical_field_27607_2(self):
        for rec in self:
            state = [('new', 'Mới'), ('sent', 'Chờ phê duyệt'), ('approved', 'Đã phê duyệt'), ('waiting', 'Chờ hủy duyệt'), ('cancel', 'Hủy')]
            rec.technical_field_27607_2 = dict(state).get(rec.en_state)

    en_nonproject_task_id = fields.Many2one('en.nonproject.task', string='Công việc ngoài dự án')

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if values.get('en_nonproject_task_id') and not values.get('account_id'):
                values['account_id'] = self.env.ref('ngsd_base.account_analytic_account_non_project_task').id
        res = super(AccountAnalyticLine, self).create(vals_list)
        res.validate_lock_create_timesheet()
        return res

    def write(self, vals):
        if 'en_state' in vals:
            for rec in self:
                if rec.en_state == 'new' and vals.get('en_state') == 'sent':
                    rec.validate_lock_create_timesheet()
                else:
                    rec.validate_lock_approve_timesheet()
        res = super(AccountAnalyticLine, self).write(vals)
        return res

    def validate_lock_create_timesheet(self):
        """check create timesheet
        employee: check timesheet employee
        timesheet_from_explanation: when create timesheet from explanation, not check lock create timesheet
        not lock_approve_timesheet: not check lock create timesheet
        holiday_id or global_leave_id: not check lock create timesheet
        """
        for rec in self:
            if rec.igone_validate_lock_timesheet():
                continue
            employee = rec.employee_id
            if employee.lock_create_timesheet:
                date_lock = (employee.lock_create_timesheet + relativedelta(hours=7)).date()
                if rec.date <= date_lock:
                    raise UserError('Bạn chỉ có thể khai timesheet sau ngày %s'%date_lock)

    def validate_lock_approve_timesheet(self):
        """check approve timesheet
        employee: check user employee
        timesheet_from_explanation: when create timesheet from explanation, not check lock approve timesheet
        not lock_approve_timesheet: not check lock approve timesheet
        holiday_id or global_leave_id: not check lock approve timesheet
        """
        employee = self.env.user.employee_id
        if not employee.lock_approve_timesheet:
            return
        date_lock = (employee.lock_approve_timesheet + relativedelta(hours=7)).date()
        for rec in self:
            if rec.igone_validate_lock_timesheet():
                continue
            if rec.date <= date_lock:
                raise UserError('Bạn chỉ có thể chỉnh sửa timesheet sau ngày %s' % date_lock)

    def igone_validate_lock_timesheet(self):
        self.ensure_one()
        if self._context.get('timesheet_from_explanation'):
            return True
        if self.holiday_id or self.global_leave_id:
            return True
        return False

    en_project_stage_id = fields.Many2one('en.project.stage', string='Giai đoạn dự án',
                                          compute='_get_en_project_stage_id', store=True, readonly=False)

    @api.depends('task_id', 'task_id.en_task_position', 'task_id.en_task_position.project_stage_id')
    def _get_en_project_stage_id(self):
        for rec in self:
            rec.en_project_stage_id = rec.task_id.en_task_position.project_stage_id

    en_project_stage_name = fields.Char('Tên giai đoạn')

    en_workpackage_id = fields.Many2one('en.workpackage', 'Gói công việc', compute='_compute_workpackage')
    total_hours_timesheet = fields.Float('Tổng số giờ đã duyệt', compute_sudo=True, compute='_compute_total_hours_timesheet', store=True)

    @api.depends('unit_amount', 'en_state', 'ot_state', 'ot_time')
    def _compute_total_hours_timesheet(self):
        for rec in self:
            total_hours_timesheet = 0
            if rec.en_state in ['approved', 'waiting']:
                total_hours_timesheet += rec.unit_amount
            if rec.ot_state == 'approved':
                total_hours_timesheet += rec.ot_time
            rec.total_hours_timesheet = total_hours_timesheet

    def _compute_workpackage(self):
        for rec in self:
            rec.en_workpackage_id = False
            if rec.task_id.en_task_position:
                rec.en_workpackage_id = rec.task_id.en_task_position

    def action_approve_timesheet(self):
        permission_user = self.env.user.has_group('hr_timesheet.group_hr_timesheet_user,ngsd_base.group_pm')
        if not permission_user:
            if not (rec.en_nonproject_task_id for rec in self):
                raise UserError('Bạn không có quyền duyệt')
            if any(rec.en_state != 'sent' or not rec.en_approve_ok for rec in self):
                raise UserError('Bản ghi của bạn không đủ điều kiện duyệt')
            for rec in self:
                rec.en_button_approved()
        else:
            if any(rec.en_state != 'sent' or not rec.en_approve_ok for rec in self):
                raise UserError('Bản ghi của bạn không đủ điều kiện duyệt')
            for rec in self:
                rec.en_button_approved()

    def action_reject_timesheet(self):
        permission_user = self.env.user.has_group('hr_timesheet.group_hr_timesheet_user,ngsd_base.group_pm')
        if not permission_user:
            if not (rec.en_nonproject_task_id for rec in self):
                raise UserError('Bạn không có quyền từ chối')
            if any(rec.en_state != 'sent' or not rec.en_approve_ok for rec in self):
                raise UserError('Bản ghi của bạn không đủ điều kiện để từ chối')
            for rec in self:
                rec.en_button_cancel()
        else:
            if any(rec.en_state != 'sent' or not rec.en_approve_ok for rec in self):
                raise UserError('Bản ghi của bạn không đủ điều kiện để từ chối')
            for rec in self:
                rec.en_button_cancel()

    def action_change_task_timesheet(self):
        if any(rec.en_nonproject_task_id.en_task_type != 'waiting_task' for rec in self):
            raise UserError('Bạn chỉ có thể Chuyển timesheet với Loại công việc là "Công việc trong dự án đang chờ"')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Chuyển timesheet',
            'res_model': 'change.task.timesheet',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_timesheet_ids': [(6, 0, self.ids)],
            },
            'views': [[False, 'form']],
        }

    def action_cancel_cancel_timesheet(self):
        if any(rec.en_state != 'waiting' or not rec.en_approve_ok for rec in self):
            raise UserError('Bản ghi của bạn không đủ điều kiện để từ chối hủy duyệt')
        for rec in self:
            rec.en_button_cancel_cancel()

    def approve_timesheet_info(self):
        for record in self:
            record.approver = self.env.user.employee_id
            record.approve_date = fields.Datetime.now()