from odoo import fields, models, api, _
from odoo import models, fields, api, exceptions
from odoo.exceptions import UserError
from odoo.addons.hr_holidays.models.hr_leave import HolidaysRequest, DummyAttendance
try:
    from odoo.addons.resource.models.resource import float_to_time, HOURS_PER_DAY, Intervals
except ImportError:
    try:
        from odoo.addons.resource.models.resource_mixin import float_to_time, HOURS_PER_DAY, Intervals
    except ImportError:
        # Fallback for Odoo 18 - these might be in different location or have different names
        try:
            from odoo.tools import float_to_time
            HOURS_PER_DAY = 8
            Intervals = None  # Will need to handle this separately
        except ImportError:
            # Define fallbacks
            def float_to_time(hours):
                return f"{int(hours):02d}:{int((hours % 1) * 60):02d}"
            HOURS_PER_DAY = 8
            Intervals = None
# không được import date ở đây
from datetime import datetime, timedelta, time
from pytz import timezone, UTC
from odoo.tools import float_compare, float_round
from collections import defaultdict
from dateutil.relativedelta import relativedelta
from odoo.exceptions import AccessError, UserError, ValidationError


def new_write(self, values):
    # is_officer = self.env.user.has_group('hr_holidays.group_hr_holidays_user') or self.env.is_superuser()
    # if not is_officer and values.keys() - {'attachment_ids', 'supported_attachment_ids', 'message_main_attachment_id'}:
    #     if any(hol.date_from.date() < fields.Date.today() and hol.employee_id.leave_manager_id != self.env.user for hol
    #            in self):
    #         raise UserError(_('You must have manager rights to modify/validate a time off that already begun'))

    # Unlink existing resource.calendar.leaves for validated time off
    if 'state' in values and values['state'] != 'validate':
        validated_leaves = self.filtered(lambda l: l.state == 'validate')
        validated_leaves._remove_resource_leave()

    employee_id = values.get('employee_id', False)
    if not self.env.context.get('leave_fast_create'):
        if values.get('state'):
            self._check_approval_update(values['state'])
            if any(holiday.validation_type == 'both' for holiday in self):
                if values.get('employee_id'):
                    employees = self.env['hr.employee'].browse(values.get('employee_id'))
                else:
                    employees = self.mapped('employee_id')
                self._check_double_validation_rules(employees, values['state'])
        if 'date_from' in values:
            values['request_date_from'] = values['date_from']
        if 'date_to' in values:
            values['request_date_to'] = values['date_to']
    result = super(HolidaysRequest, self).write(values)
    if not self.env.context.get('leave_fast_create'):
        for holiday in self:
            if employee_id:
                holiday.add_follower(employee_id)

    return result

HolidaysRequest.write = new_write


class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    use_leave_time_slot = fields.Boolean(string="Sử dụng khung giờ nửa buổi", default=False)
    virtual_advance_leave = fields.Float('Phép ứng', compute='_compute_leaves')
    virtual_advance_leave_taken = fields.Float('Phép đã ứng', compute='_compute_leaves')

    @api.depends('requires_allocation')
    def _compute_valid(self):
        super(HrLeaveType, self)._compute_valid()
        employee_id = self._context.get('default_employee_id', self._context.get('employee_id', self.env.user.employee_id.id))
        if employee_id and self.env['hr.employee'].browse(employee_id).state_hr_employee != 'permanent':
            for holiday_type in self:
                if holiday_type.code == 'P':
                    holiday_type.has_valid_allocation = False

    @api.model
    def _search_valid(self, operator, value):
        res = super()._search_valid(operator, value)
        employee_id = self._context.get('default_employee_id', self._context.get('employee_id')) or self.env.user.employee_id.id
        if employee_id and self.env['hr.employee'].browse(employee_id).state_hr_employee != 'permanent':
            return [('id', 'in', [id for id in res[0][2] if self.browse(id).code != 'P'])]
        return res

    @api.depends_context('employee_id', 'default_employee_id')
    def _compute_leaves(self):
        data_days = {}
        employee_id = self._get_contextual_employee_id()

        if employee_id:
            data_days = (self.get_employees_days(employee_id)[employee_id[0]] if isinstance(employee_id, list) else
                         self.get_employees_days([employee_id])[employee_id])

        for holiday_status in self:
            result = data_days.get(holiday_status.id, {})
            holiday_status.max_leaves = result.get('max_leaves', 0)
            holiday_status.leaves_taken = result.get('leaves_taken', 0)
            holiday_status.remaining_leaves = result.get('remaining_leaves', 0)
            holiday_status.virtual_remaining_leaves = result.get('virtual_remaining_leaves', 0)
            holiday_status.virtual_leaves_taken = result.get('virtual_leaves_taken', 0)
            holiday_status.virtual_advance_leave = result.get('virtual_advance_leave', 0)
            holiday_status.virtual_advance_leave_taken = result.get('virtual_advance_leave_taken', 0)

    def _get_employees_days_per_allocation(self, employee_ids, date=None):
        leaves = self.env['hr.leave'].search([
            ('employee_id', 'in', employee_ids),
            ('state', 'in', ['confirm', 'validate1', 'validate']),
            ('holiday_status_id', 'in', self.ids)
        ])

        allocations = self.env['hr.leave.allocation'].with_context(active_test=False).search([
            ('employee_id', 'in', employee_ids),
            ('state', 'in', ['validate']),
            ('holiday_status_id', 'in', self.ids),
        ])

        if not date:
            date = fields.Date.to_date(self.env.context.get('default_date_from')) or fields.Date.Date.Date.context_today(self)

        # The allocation_employees dictionary groups the allocations based on the employee and the holiday type
        # The structure is the following:
        # - KEYS:
        # allocation_employees
        #   |--employee_id
        #      |--holiday_status_id
        # - VALUES:
        # Intervals with the start and end date of each allocation and associated allocations within this interval
        allocation_employees = defaultdict(lambda: defaultdict(list))

        ### Creation of the allocation intervals ###
        for holiday_status_id in allocations.holiday_status_id:
            for employee_id in employee_ids:
                if Intervals is not None:
                    allocation_intervals = Intervals([(
                        fields.datetime.combine(allocation.date_from, time.min),
                        fields.datetime.combine(allocation.date_to or fields.date.max, time.max),
                        allocation)
                        for allocation in allocations.filtered(lambda allocation: allocation.employee_id.id == employee_id and allocation.holiday_status_id == holiday_status_id)])
                else:
                    # Fallback: use simple list for Odoo 18
                    allocation_intervals = [(
                        fields.datetime.combine(allocation.date_from, time.min),
                        fields.datetime.combine(allocation.date_to or fields.date.max, time.max),
                        allocation)
                        for allocation in allocations.filtered(lambda allocation: allocation.employee_id.id == employee_id and allocation.holiday_status_id == holiday_status_id)]

                allocation_employees[employee_id][holiday_status_id] = allocation_intervals

        # The leave_employees dictionary groups the leavess based on the employee and the holiday type
        # The structure is the following:
        # - KEYS:
        # leave_employees
        #   |--employee_id
        #      |--holiday_status_id
        # - VALUES:
        # Intervals with the start and end date of each leave and associated leave within this interval
        leaves_employees = defaultdict(lambda: defaultdict(list))
        leave_intervals = []

        ### Creation of the leave intervals ###
        if leaves:
            for holiday_status_id in leaves.holiday_status_id:
                for employee_id in employee_ids:
                    if Intervals is not None:
                        leave_intervals = Intervals([(
                            fields.datetime.combine(leave.date_from, time.min),
                            fields.datetime.combine(leave.date_to, time.max),
                            leave)
                            for leave in leaves.filtered(lambda leave: leave.employee_id.id == employee_id and leave.holiday_status_id == holiday_status_id)])
                    else:
                        # Fallback: use simple list for Odoo 18
                        leave_intervals = [(
                            fields.datetime.combine(leave.date_from, time.min),
                            fields.datetime.combine(leave.date_to, time.max),
                            leave)
                            for leave in leaves.filtered(lambda leave: leave.employee_id.id == employee_id and leave.holiday_status_id == holiday_status_id)]

                    leaves_employees[employee_id][holiday_status_id] = leave_intervals

        # allocation_days_consumed is a dictionary to map the number of days/hours of leaves taken per allocation
        # The structure is the following:
        # - KEYS:
        # allocation_days_consumed
        #  |--employee_id
        #      |--holiday_status_id
        #          |--allocation
        #              |--virtual_leaves_taken
        #              |--leaves_taken
        #              |--virtual_remaining_leaves
        #              |--remaining_leaves
        #              |--virtual_advance_leave
        #              |--virtual_advance_leave_taken
        #              |--max_leaves
        # - VALUES:
        # Integer representing the number of (virtual) remaining leaves, (virtual) leaves taken or max leaves for each allocation.
        # The unit is in hour or days depending on the leave type request unit
        allocations_days_consumed = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: 0))))

        company_domain = [('company_id', 'in', list(set(self.env.company.ids + self.env.context.get('allowed_company_ids', []))))]

        ### Existing leaves assigned to allocations ###
        if leaves_employees:
            for employee_id, leaves_interval_by_status in leaves_employees.items():
                for holiday_status_id in leaves_interval_by_status:
                    days_consumed = allocations_days_consumed[employee_id][holiday_status_id]
                    if allocation_employees[employee_id][holiday_status_id]:
                        allocations = allocation_employees[employee_id][holiday_status_id] & leaves_interval_by_status[holiday_status_id]
                        available_allocations = self.env['hr.leave.allocation']
                        # Handle both Intervals object and list fallback
                        allocation_items = allocations._items if hasattr(allocations, '_items') else allocations
                        for allocation_interval in allocation_items:
                            available_allocations |= allocation_interval[2]
                        # Consume the allocations that are close to expiration first
                        sorted_available_allocations = available_allocations.filtered(lambda allocation: allocation.date_to and not allocation.use_advance_leave).sorted(key='date_to')
                        sorted_available_allocations += available_allocations.filtered(lambda allocation: allocation.date_to and allocation.use_advance_leave).sorted(key='date_to')
                        sorted_available_allocations += available_allocations.filtered(lambda allocation: not allocation.date_to and not allocation.use_advance_leave)
                        sorted_available_allocations += available_allocations.filtered(lambda allocation: not allocation.date_to and allocation.use_advance_leave)
                        leave_interval_obj = leaves_interval_by_status[holiday_status_id]
                        leave_intervals = leave_interval_obj._items if hasattr(leave_interval_obj, '_items') else leave_interval_obj
                        for leave_interval in leave_intervals:
                            leaves = leave_interval[2]
                            for leave in leaves:
                                if leave.leave_type_request_unit in ['day', 'half_day'] or (leave.leave_type_request_unit == 'hour' and leave.use_leave_time_slot):
                                    leave_duration = leave.number_of_days
                                    leave_unit = 'days'
                                else:
                                    leave_duration = leave.number_of_hours_display
                                    leave_unit = 'hours'
                                if holiday_status_id.requires_allocation != 'no':
                                    for available_allocation in sorted_available_allocations:
                                        if (available_allocation.date_to and available_allocation.date_to < leave.date_from.date()) \
                                            or (available_allocation.date_from > leave.date_to.date()):
                                            continue
                                        virtual_remaining_leaves = (available_allocation.total_number_of_days if leave_unit == 'days' else available_allocation.number_of_hours_display) - allocations_days_consumed[employee_id][holiday_status_id][available_allocation]['virtual_leaves_taken']
                                        max_leaves = min(virtual_remaining_leaves, leave_duration)
                                        days_consumed[available_allocation]['virtual_leaves_taken'] += max_leaves
                                        days_consumed[available_allocation]['virtual_advance_leave_taken'] += leave.advance_leave
                                        if leave.state == 'validate':
                                            days_consumed[available_allocation]['leaves_taken'] += max_leaves
                                        leave_duration -= max_leaves
                                    if leave_duration > 0:
                                        # There are not enough allocation for the number of leaves
                                        days_consumed[False]['virtual_remaining_leaves'] -= leave_duration
                                        # Hack to make sure that a sum of several allocations does not hide an error
                                        days_consumed['error']['virtual_remaining_leaves'] -= leave_duration
                                else:
                                    days_consumed[False]['virtual_leaves_taken'] += leave_duration
                                    if leave.state == 'validate':
                                        days_consumed[False]['leaves_taken'] += leave_duration

        # Future available leaves
        for employee_id, allocation_intervals_by_status in allocation_employees.items():
            for holiday_status_id, intervals in allocation_intervals_by_status.items():
                if not intervals:
                    continue
                future_allocation_intervals = intervals & Intervals([(
                    fields.datetime.combine(date, time.min),
                    fields.datetime.combine(date, time.max) + timedelta(days=5*365),
                    self.env['hr.leave'])])
                search_date = date
                future_intervals = future_allocation_intervals._items if hasattr(future_allocation_intervals, '_items') else future_allocation_intervals
                for future_allocation_interval in future_intervals:
                    if future_allocation_interval[0].date() > search_date:
                        continue
                    employee_quantity_available = future_allocation_interval[2].employee_id._get_work_days_data_batch(
                        future_allocation_interval[0],
                        future_allocation_interval[1],
                        compute_leaves=False,
                        domain=company_domain)[employee_id]
                    for allocation in future_allocation_interval[2]:
                        if not allocation.active or allocation.date_from > search_date:
                            continue
                        number_of_days = allocation.total_number_of_days
                        days_consumed = allocations_days_consumed[employee_id][holiday_status_id][allocation]
                        if future_allocation_interval[1] != fields.datetime.combine(date, time.max) + timedelta(days=5*365):
                            quantity_available = employee_quantity_available
                        else:
                            # If no end date to the allocation, consider the number of days remaining as infinite
                            quantity_available = {'days': float('inf'), 'hours': float('inf')}
                        if allocation.type_request_unit in ['day', 'half_day']:
                            quantity_available = quantity_available['days']
                            remaining_days_allocation = (number_of_days - days_consumed['virtual_leaves_taken'])
                        else:
                            quantity_available = quantity_available['hours']
                            remaining_days_allocation = (allocation.number_of_hours_display - days_consumed['virtual_leaves_taken'])
                        if quantity_available <= remaining_days_allocation:
                            search_date = future_allocation_interval[1].date() + timedelta(days=1)
                        days_consumed['virtual_remaining_leaves'] += min(quantity_available, remaining_days_allocation)
                        days_consumed['max_leaves'] = number_of_days if allocation.type_request_unit in ['day', 'half_day'] else allocation.number_of_hours_display
                        days_consumed['remaining_leaves'] = days_consumed['max_leaves'] - days_consumed['leaves_taken']
                        days_consumed['virtual_advance_leave'] = allocation.number_of_days - days_consumed['virtual_leaves_taken']
                        if remaining_days_allocation >= quantity_available:
                            break

        return allocations_days_consumed


    def get_employees_days(self, employee_ids, date=None):
        self = self.with_context(igone_recompute_advance_leave=True)
        result = {
            employee_id: {
                leave_type.id: {
                    'max_leaves': 0,
                    'leaves_taken': 0,
                    'remaining_leaves': 0,
                    'virtual_remaining_leaves': 0,
                    'virtual_leaves_taken': 0,
                    'virtual_advance_leave': 0,
                    'virtual_advance_leave_taken': 0,
                } for leave_type in self
            } for employee_id in employee_ids
        }

        if not date:
            date = fields.Date.to_date(self.env.context.get('default_date_from')) or fields.Date.Date.Date.context_today(self)

        allocations_days_consumed = self._get_employees_days_per_allocation(employee_ids, date)

        leave_keys = ['max_leaves', 'leaves_taken', 'remaining_leaves', 'virtual_remaining_leaves', 'virtual_leaves_taken', 'virtual_advance_leave', 'virtual_advance_leave_taken']

        for employee_id in allocations_days_consumed:
            for holiday_status_id in allocations_days_consumed[employee_id]:
                if allocations_days_consumed[employee_id][holiday_status_id].get('error'):
                    for leave_key in leave_keys:
                        result[employee_id][holiday_status_id if isinstance(holiday_status_id, int) else holiday_status_id.id][leave_key] = allocations_days_consumed[employee_id][holiday_status_id]['error'][leave_key]
                    continue
                for allocation in allocations_days_consumed[employee_id][holiday_status_id]:
                    if allocation and allocation.date_to and (allocation.date_to < date or allocation.date_from > date):
                        continue
                    for leave_key in leave_keys:
                        result[employee_id][holiday_status_id if isinstance(holiday_status_id, int) else holiday_status_id.id][leave_key] += allocations_days_consumed[employee_id][holiday_status_id][allocation][leave_key]

        return result

    def _get_days_request(self):
        self.ensure_one()
        request_unit = self.request_unit
        if request_unit == 'hour' and self.use_leave_time_slot:
            request_unit = 'half_day'
        return (self.name, {
                'remaining_leaves': ('%.2f' % self.remaining_leaves).rstrip('0').rstrip('.'),
                'virtual_remaining_leaves': ('%.2f' % self.virtual_advance_leave).rstrip('0').rstrip('.'),
                'max_leaves': ('%.2f' % self.max_leaves).rstrip('0').rstrip('.'),
                'leaves_taken': ('%.2f' % self.leaves_taken).rstrip('0').rstrip('.'),
                'virtual_leaves_taken': ('%.2f' % self.virtual_leaves_taken).rstrip('0').rstrip('.'),
                'request_unit': request_unit,
                'icon': self.sudo().icon_id.url,
                }, self.requires_allocation, self.id)

    @api.model
    def get_days_all_request(self):
        _domain = []
        if self.env.user.employee_id.state_hr_employee in ["inter", "training", "probation", "contract_lease"]:
            _domain = [('name', '!=', 'Có phép')]
        leave_types = sorted(self.search(_domain).filtered(lambda x: ((x.virtual_remaining_leaves > 0 and x.max_leaves or x.virtual_advance_leave < 0))), key=self._model_sorting_key, reverse=True)
        return [lt._get_days_request() for lt in leave_types]

    def name_get(self):
        if not self._context.get('employee_id'):
            # leave counts is based on employee_id, would be inaccurate if not based on correct employee
            return super(HrLeaveType, self).name_get()
        res = []
        for record in self:
            name = record.name
            if record.requires_allocation == "yes" and not self._context.get('from_manager_leave_form'):
                name = "%(name)s (%(count)s)" % {
                    'name': name,
                    'count': _('%g remaining out of %g') % (
                        float_round(record.virtual_remaining_leaves, precision_digits=2) or 0.0,
                        float_round(record.max_leaves, precision_digits=2) or 0.0,
                    ) + (_(' hours') if record.request_unit == 'hour' and not record.use_leave_time_slot else _(' days'))
                }
            res.append((record.id, name))
        return res

class HolidaysAllocation(models.Model):
    _inherit = 'hr.leave.allocation'

    type_request_unit = fields.Selection([
        ('day', 'Ngày'),
        ('half_day', 'Nửa ngày'),
        ('hour', 'Giờ')], related=False, readonly=True, compute='_get_type_request_unit')

    advance_leave = fields.Float('Số phép ứng', compute='_get_advance_leave', store=True)
    use_advance_leave = fields.Boolean('Sử dụng phép ứng', default=False)
    total_number_of_days = fields.Float('Tổng số ngày', compute='_compute_total_number_of_days')

    @api.depends('number_of_days', 'use_advance_leave', 'employee_id', 'employee_id.en_date_start', 'employee_id.departure_date')
    def _get_advance_leave(self):
        """
        Tính số phép ứng
        ví dụ nhân viên từ đầu năm
        tháng    tổng phép    số phép đã cấp    số phép ứng
        1       6               1               5
        2       6               2               4
        3       6               3               3
        4       9               4               5
        ví dụ nhân vien từ t3
        tháng    tổng phép    số phép đã cấp    số phép ứng
        1       0               0               0
        2       0               0               0
        3       4               1               3
        4       7               2               5
        5       7               3               4

        """
        for rec in self:
            advance_leave = 0
            employee = rec.employee_id
            if employee and rec.use_advance_leave and employee.en_date_start and relativedelta(employee.departure_date or fields.Date.Date.Date.context_today(self), employee.en_date_start).years > 0:
                total_number_of_days = rec.number_of_days
                current_month = fields.Date.Date.Date.context_today(self).month
                total_number_of_days_by_month = (current_month // 3 + 2) * 3
                current_level = rec.accrual_plan_id.level_ids[:1]
                if rec.allocation_type == 'accrual' and current_level.maximum_leave and current_level.added_value_type == "days":
                    total_number_of_days_by_month = min(total_number_of_days_by_month, current_level.maximum_leave)
                advance_leave = total_number_of_days_by_month - (current_month - total_number_of_days) - total_number_of_days
            rec.advance_leave = advance_leave

    @api.depends('number_of_days', 'advance_leave')
    def _compute_total_number_of_days(self):
        for rec in self:
            total_number_of_days = rec.number_of_days
            employee = rec.employee_id
            if employee and rec.use_advance_leave and employee.en_date_start and relativedelta(employee.departure_date or fields.Date.Date.Date.context_today(self), employee.en_date_start).years > 0:
                total_number_of_days += rec.advance_leave
                current_level = rec.accrual_plan_id.level_ids[:1]
                if rec.allocation_type == 'accrual' and current_level.maximum_leave and current_level.added_value_type == "days":
                    total_number_of_days = min(total_number_of_days, current_level.maximum_leave)
            rec.total_number_of_days = total_number_of_days

    @api.depends('number_of_days', 'advance_leave')
    def _compute_total_number_of_days(self):
        for rec in self:
            total_number_of_days = rec.number_of_days
            employee = rec.employee_id
            if employee and employee.en_date_start and relativedelta(employee.departure_date or fields.Date.Date.Date.context_today(self), employee.en_date_start).years > 0:
                total_number_of_days += rec.advance_leave
                current_level = rec.accrual_plan_id.level_ids[:1]
                if rec.allocation_type == 'accrual' and current_level.maximum_leave and current_level.added_value_type == "days":
                    total_number_of_days = min(total_number_of_days, current_level.maximum_leave)
            rec.total_number_of_days = total_number_of_days

    @api.depends('holiday_status_id')
    def _get_type_request_unit(self):
        for rec in self:
            type_request_unit = rec.holiday_status_id.request_unit
            if type_request_unit == 'hour' and rec.holiday_status_id.use_leave_time_slot:
                type_request_unit = 'half_day'
            rec.type_request_unit = type_request_unit


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    use_leave_time_slot = fields.Boolean(related='holiday_status_id.use_leave_time_slot')
    use_time_slot = fields.Boolean('Nửa buổi', compute='_compute_use_time_slot', store=True, readonly=False)

    time_slot = fields.Selection([
        ('morning_half', 'Nửa đầu buổi sáng'),
        ('morning_late', 'Nửa cuối buổi sáng'),
        ('afternoon_half', 'Nửa đầu buổi chiều'),
        ('afternoon_late', 'Nửa cuối buổi chiều')
    ], string="Khung giờ nửa buổi", default='morning_half')

    request_hour_from = fields.Char(compute="_compute_hour_from", store=True)
    request_hour_to = fields.Char(compute="_compute_hour_to", store=True)
    request_unit_custom = fields.Boolean('Custom Unit Request', default=False,
                                        help="Allow custom time unit request")
    number_of_hours_display = fields.Float('Display Hours', compute='_compute_number_of_hours_display', store=True)
    number_of_days_display = fields.Float('Display Days', compute='_compute_number_of_days_display', store=True)
    advance_leave = fields.Float('Số phép ứng', compute='_get_is_advance_leave', store=True)

    employee_ids = fields.Many2many(
        'hr.employee', compute='_compute_from_holiday_type', store=True, string='Employees', readonly=False,
        groups="hr_holidays.group_hr_holidays_user",
        states={'cancel': [('readonly', True)], 'refuse': [('readonly', True)], 'confirm': [('readonly', True)],
                'validate1': [('readonly', True)], 'validate': [('readonly', True)]})

    holiday_type = fields.Selection([
        ('employee', 'By Employee'),
        ('company', 'By Company'),
        ('department', 'By Department'),
        ('category', 'By Employee Tag')],
        string='Allocation Mode', readonly=True, required=True, default='employee',
        states={'draft': [('readonly', False)]},
        help='By Employee: Allocation/Request for individual Employee, By Employee Tag: Allocation/Request for group of employees in category')

    holiday_status_id = fields.Many2one(
        "hr.leave.type", compute='_compute_from_employee_id', store=True, string="Time Off Type", required=True,
        readonly=False,
        states={'cancel': [('readonly', True)], 'confirm': [('readonly', True)], 'refuse': [('readonly', True)],
                'validate1': [('readonly', True)], 'validate': [('readonly', True)]},
        domain=['|', ('requires_allocation', '=', 'no'), ('has_valid_allocation', '=', True)])

    def read(self, fields=None, load='_classic_read'):
        if not fields or 'advance_leave' in fields:
            self.filtered(lambda d: d.state == 'draft').recompute_advance_leave()
        return super().read(fields, load)

    @api.depends('holiday_status_id', 'request_date_from', 'request_date_to', 'state')
    def _get_is_advance_leave(self):
        for rec in self:
            advance_leave = rec._get_number_advance_leave()
            rec.advance_leave = advance_leave

    def recompute_advance_leave(self):
        for rec in self:
            advance_leave = rec._get_number_advance_leave()
            if rec.advance_leave != advance_leave:
                rec.advance_leave = advance_leave

    @api.constrains('state')
    def _en_constrains_request_hour(self):
        if self.state != 'draft':  # chỉ check khi không còn ở trạng thái nháp
            for rec in self:
                start_date = rec.date_from.date()  # lấy phần ngày
                end_date = rec.date_to.date()

                current_date = start_date
                while current_date <= end_date:
                    lines = self.env['account.analytic.line'].search([
                        ('employee_id', '=', rec.employee_id.id),
                        ('date', '=', current_date),
                        ('en_state', '!=', 'cancel'),
                        ('en_state', '!=', 'new')
                    ])
                    amount = sum(lines.mapped('unit_amount')) + rec.number_of_hours_display / (rec.number_of_days if rec.number_of_days > 1 else 1)

                    # Ví dụ kiểm tra logic
                    if amount > 8:
                        if self.holiday_status_id.code == 'W':
                            if amount > 16:
                                raise exceptions.ValidationError(
                                    f"Đã khai tổng {amount} giờ trong ngày {current_date.strftime('%d/%m/%Y')}, vượt quá giới hạn 8h!"
                                )
                        else:
                            raise exceptions.ValidationError(
                                f"Đã khai tổng {amount} giờ trong ngày {current_date.strftime('%d/%m/%Y')}, vượt quá giới hạn 8h!"
                            )

                    current_date += timedelta(days=1)

    def _get_number_advance_leave(self):
        if self.state != 'draft':
            return self.advance_leave
        if not self.holiday_status_id or not self.employee_id:
            return 0
        leave_days = self.holiday_status_id.get_employees_days(self.employee_id.ids)[self.employee_id.id][self.holiday_status_id.id]
        advance_leave = max(leave_days['virtual_advance_leave'] + leave_days['virtual_advance_leave_taken'], 0) - self.number_of_days
        return advance_leave < 0 and abs(advance_leave)

    @api.depends('number_of_hours')
    def _compute_number_of_hours_display(self):
        for leave in self:
            leave.number_of_hours_display = leave.number_of_hours

    @api.depends('number_of_days')
    def _compute_number_of_days_display(self):
        for leave in self:
            leave.number_of_days_display = leave.number_of_days

    @api.constrains('request_hour_from', 'request_hour_to')
    def check_valid_request_hour(self):
        for rec in self:
            try:
                float(rec.request_hour_from)
            except:
                raise UserError('Thời điểm bắt đầu không hợp lệ (00:00-23:59)')
            try:
                float(rec.request_hour_to)
            except:
                raise UserError('Thời điểm kết thúc không hợp lệ (00:00-24)')

            if not (0 <= float(rec.request_hour_from) <= 23.99):
                raise UserError('Thời điểm bắt đầu không hợp lệ (00:00-23:59)')
            if not (0 <= float(rec.request_hour_to) <= 24):
                raise UserError('Thời điểm kết thúc không hợp lệ (00:00-24)')
            if float(rec.request_hour_from) > float(rec.request_hour_to):
                raise UserError('Thời điểm bắt đầu phải nhỏ hơn Thời điểm kết thúc')

    @api.onchange('time_slot', 'use_time_slot', 'request_date_from', 'request_date_to')
    def _onchange_time_slot(self):
        if self.use_time_slot and self.request_date_from and self.request_date_to:
            resource_calendar_id = self.employee_id.resource_calendar_id or self.env.company.resource_calendar_id
            domain = [('calendar_id', '=', resource_calendar_id.id), ('display_type', '=', False)]
            attendances = self.env['resource.calendar.attendance'].read_group(domain, ['ids:array_agg(id)', 'hour_from:min(hour_from)', 'hour_to:max(hour_to)', 'week_type', 'dayofweek', 'day_period'],
                                                                              ['week_type', 'dayofweek', 'day_period'],
                                                                              lazy=False)

            # Must be sorted by dayofweek ASC and day_period DESC
            attendances = sorted([DummyAttendance(group['hour_from'], group['hour_to'], group['dayofweek'], group['day_period'], group['week_type']) for group in attendances], key=lambda att: (att.dayofweek, att.day_period != 'morning'))

            default_value = DummyAttendance(0, 0, 0, 'morning', False)
            attendance_from = next((att for att in attendances if int(att.dayofweek) >= self.request_date_from.weekday()), attendances[0] if attendances else default_value)
            # find last attendance coming before last_day
            attendance_to = next((att for att in reversed(attendances) if int(att.dayofweek) <= self.request_date_to.weekday()), attendances[-1] if attendances else default_value)
            time_slot = self.time_slot
            if not time_slot:
                time_slot = 'morning_half'
            attendance = attendance_to if 'afternoon'in time_slot else attendance_from
            if 'half' in time_slot:
                hour_from = attendance.hour_from
                hour_to = (attendance.hour_from + attendance.hour_to) / 2
            else:
                hour_from = (attendance.hour_from + attendance.hour_to) / 2
                hour_to = attendance.hour_to
            self.request_hour_from = "%.2f" % hour_from
            self.request_hour_to = "%.2f" % hour_to

    @api.depends('holiday_status_id', 'request_unit_half', 'request_unit_custom')
    def _compute_use_time_slot(self):
        for holiday in self:
            if holiday.holiday_status_id or holiday.request_unit_half or holiday.request_unit_custom:
                holiday.use_time_slot = False

    @api.depends('holiday_status_id', 'request_unit_half', 'request_unit_custom', 'use_time_slot')
    def _compute_request_unit_hours(self):
        res = super()._compute_request_unit_hours()
        for holiday in self:
            if holiday.leave_type_request_unit == 'hour' and holiday.use_leave_time_slot:
                holiday.request_unit_hours = holiday.use_time_slot

    def _get_number_of_days(self, date_from, date_to, employee_id):
        """ Chỉnh sửa nửa buổi 0.25 ngày
        """
        result = super(HrLeave, self)._get_number_of_days(date_from, date_to, employee_id)
        if self.use_time_slot and result['hours'] > 0:
            result['days'] = 0.25
        return result

    @api.depends('number_of_days_display', 'holiday_status_id')
    def _compute_duration_display(self):
        super(HrLeave, self)._compute_duration_display()
        for leave in self:
            if leave.use_leave_time_slot:
                leave.duration_display = '%g %s' % (float_round(leave.number_of_days_display, precision_digits=2), _('ngày'))

    @api.depends('request_date_from_period', 'request_hour_from', 'request_hour_to', 'request_date_from', 'request_date_to',
                'request_unit_half', 'request_unit_hours', 'request_unit_custom', 'employee_id', 'use_time_slot', 'time_slot')
    def _compute_date_from_to(self):
        for holiday in self:
            if holiday.request_date_from and (not holiday.request_date_to or holiday.request_date_from > holiday.request_date_to):
                holiday.request_date_to = holiday.request_date_from
            if not holiday.request_date_from:
                holiday.date_from = False
            elif not holiday.request_unit_half and not holiday.request_unit_hours and not holiday.request_date_to:
                holiday.date_to = False
            else:
                if holiday.request_unit_half or holiday.request_unit_hours:
                    holiday.request_date_to = holiday.request_date_from
                resource_calendar_id = holiday.employee_id.resource_calendar_id or self.env.company.resource_calendar_id
                domain = [('calendar_id', '=', resource_calendar_id.id), ('display_type', '=', False)]
                attendances = self.env['resource.calendar.attendance'].read_group(domain, ['ids:array_agg(id)', 'hour_from:min(hour_from)', 'hour_to:max(hour_to)', 'week_type', 'dayofweek', 'day_period'], ['week_type', 'dayofweek', 'day_period'], lazy=False)

                # Must be sorted by dayofweek ASC and day_period DESC
                attendances = sorted([DummyAttendance(group['hour_from'], group['hour_to'], group['dayofweek'], group['day_period'], group['week_type']) for group in attendances], key=lambda att: (att.dayofweek, att.day_period != 'morning'))

                default_value = DummyAttendance(0, 0, 0, 'morning', False)

                if resource_calendar_id.two_weeks_calendar:
                    # find week type of start_date
                    start_week_type = self.env['resource.calendar.attendance'].get_week_type(holiday.request_date_from)
                    attendance_actual_week = [att for att in attendances if att.week_type is False or int(att.week_type) == start_week_type]
                    attendance_actual_next_week = [att for att in attendances if att.week_type is False or int(att.week_type) != start_week_type]
                    # First, add days of actual week coming after date_from
                    attendance_filtred = [att for att in attendance_actual_week if int(att.dayofweek) >= holiday.request_date_from.weekday()]
                    # Second, add days of the other type of week
                    attendance_filtred += list(attendance_actual_next_week)
                    # Third, add days of actual week (to consider days that we have remove first because they coming before date_from)
                    attendance_filtred += list(attendance_actual_week)
                    end_week_type = self.env['resource.calendar.attendance'].get_week_type(holiday.request_date_to)
                    attendance_actual_week = [att for att in attendances if att.week_type is False or int(att.week_type) == end_week_type]
                    attendance_actual_next_week = [att for att in attendances if att.week_type is False or int(att.week_type) != end_week_type]
                    attendance_filtred_reversed = list(reversed([att for att in attendance_actual_week if int(att.dayofweek) <= holiday.request_date_to.weekday()]))
                    attendance_filtred_reversed += list(reversed(attendance_actual_next_week))
                    attendance_filtred_reversed += list(reversed(attendance_actual_week))

                    # find first attendance coming after first_day
                    attendance_from = attendance_filtred[0]
                    # find last attendance coming before last_day
                    attendance_to = attendance_filtred_reversed[0]
                else:
                    # find first attendance coming after first_day
                    attendance_from = next((att for att in attendances if int(att.dayofweek) >= holiday.request_date_from.weekday()), attendances[0] if attendances else default_value)
                    # find last attendance coming before last_day
                    attendance_to = next((att for att in reversed(attendances) if int(att.dayofweek) <= holiday.request_date_to.weekday()), attendances[-1] if attendances else default_value)

                compensated_request_date_from = holiday.request_date_from
                compensated_request_date_to = holiday.request_date_to

                if holiday.request_unit_half:
                    if holiday.request_date_from_period == 'am':
                        hour_from = float_to_time(attendance_from.hour_from)
                        hour_to = float_to_time(attendance_from.hour_to)
                    else:
                        hour_from = float_to_time(attendance_to.hour_from)
                        hour_to = float_to_time(attendance_to.hour_to)
                elif holiday.request_unit_hours:
                    hour_from = float_to_time(float(holiday.request_hour_from))
                    hour_to = float_to_time(float(holiday.request_hour_to))
                elif holiday.request_unit_custom:
                    hour_from = holiday.date_from.time()
                    hour_to = holiday.date_to.time()
                    compensated_request_date_from = holiday._adjust_date_based_on_tz(holiday.request_date_from, hour_from)
                    compensated_request_date_to = holiday._adjust_date_based_on_tz(holiday.request_date_to, hour_to)
                else:
                    hour_from = float_to_time(attendance_from.hour_from)
                    hour_to = float_to_time(attendance_to.hour_to)
                holiday.date_from = timezone(holiday.tz).localize(datetime.combine(compensated_request_date_from, hour_from)).astimezone(UTC).replace(tzinfo=None)
                holiday.date_to = timezone(holiday.tz).localize(datetime.combine(compensated_request_date_to, hour_to)).astimezone(UTC).replace(tzinfo=None)

    def _timesheet_prepare_line_values(self, index, work_hours_data, day_date, work_hours_count):
        self.ensure_one()
        self = self.sudo()
        return {
            'name': _("Nghỉ phép (%s/%s)", index + 1, len(work_hours_data)),
            'project_id': self.holiday_status_id.timesheet_project_id.id,
            'task_id': self.holiday_status_id.timesheet_task_id.id,
            'account_id': self.holiday_status_id.timesheet_project_id.analytic_account_id.id,
            'unit_amount': work_hours_count,
            'user_id': self.employee_id.user_id.id,
            'date': day_date,
            'holiday_id': self.id,
            'employee_id': self.employee_id.id,
            'company_id': self.holiday_status_id.timesheet_task_id.company_id.id or self.holiday_status_id.timesheet_project_id.company_id.id,
        }

