from odoo import models, fields, api, _
from odoo.tools.misc import format_date, DEFAULT_SERVER_DATE_FORMAT
from datetime import timedelta, datetime, time
from odoo.tools import config, date_utils, get_lang, html2plaintext
from dateutil.relativedelta import relativedelta
from decimal import localcontext, Decimal, ROUND_HALF_UP, ROUND_UP
from pytz import timezone
import math


class EffectiveResourceProjectWizard(models.TransientModel):
    _name = "effective.resource.project.report.wizard"
    _description = "Báo cáo hiệu quả nguồn lực trong dự án"

    def _default_state_ids(self):
        return self.env['project.project.stage'].search([('en_state', 'not in', ['complete', 'cancel'])]).ids

    project_id = fields.Many2one(string='Dự án', comodel_name='project.project')
    unit = fields.Selection(string='Đơn vị', selection=[('MM', 'MM'), ('MD', 'MD'), ('MH', 'MH')], default='MM', required=True)
    project_ids = fields.Many2many('project.project', string='Dự án', domain="['|', ('en_department_id', 'in', department_ids), ('en_block_id', 'in', block_ids)]")
    state_ids = fields.Many2many('project.project.stage', 'effective_resource_report_project_project_stage_rel', string="Trạng thái", default=lambda self: self._default_state_ids())
    department_ids = fields.Many2many('hr.department', string='Trung tâm', domain="[('block_id', 'in', block_ids)]")
    employee_ids = fields.Many2many('hr.employee', string='Nhân viên', domain="['|', ('department_id', 'in', department_ids), ('en_block_id', 'in', block_ids)]")
    block_ids = fields.Many2many('en.name.block', string="Khối")
    date_from = fields.Date('Từ', required=1)
    date_to = fields.Date('Đến', required=1)
    period = fields.Selection(selection=[
        ('optional', 'Tùy chọn'),
        ('this_month', 'Tháng này'),
        ('this_quarter', 'Quý này'),
        ('this_year', 'Năm nay'),
        ('previous_month', 'Tháng trước'),
        ('previous_quarter', 'Quý trước'),
        ('previous_year', 'Năm trước'),
    ], string='Kỳ báo cáo', required=1, default='this_month')

    @api.onchange('block_ids')
    def _onchange_block(self):
        for rec in self:
            rec.department_ids = False

    @api.onchange('department_ids')
    def _onchange_department(self):
        for rec in self:
            rec.employee_ids = False
            rec.project_ids = False

    @api.onchange('period')
    def onchange_period(self):
        today = fields.Date.today()
        period = self.period
        if period == 'this_month':
            start_date = today.replace(day=1)
            end_date = (today + relativedelta(months=1)).replace(day=1) - relativedelta(days=1)
        elif period == 'this_quarter':
            start_date, end_date = date_utils.get_quarter(today)
        elif period == 'this_year':
            start_date = today.replace(month=1, day=1)
            end_date = today.replace(month=12, day=31)
        elif period == 'previous_month':
            start_date = (today + relativedelta(months=-1)).replace(day=1)
            end_date = today + relativedelta(days=-today.day)
        elif period == 'previous_quarter':
            start_date = (today - relativedelta(months=(today.month - 1) % 3) - relativedelta(months=3)).replace(day=1)
            end_date = today - relativedelta(months=(today.month - 1) % 3) - relativedelta(days=today.day)
        elif period == 'previous_year':
            start_date = (today + relativedelta(years=-1)).replace(day=1, month=1)
            end_date = (today + relativedelta(years=-1)).replace(day=31, month=12)
        else:
            start_date = datetime.strptime(self._context.get('start_date') or today.strftime('%Y-%m-%d'), '%Y-%m-%d')
            end_date = datetime.strptime(self._context.get('end_date') or today.strftime('%Y-%m-%d'), '%Y-%m-%d')
        self.date_from = start_date
        self.date_to = end_date

    def do(self):
        self = self.sudo()
        action = self.env.ref('account_reports.action_effective_resource_project_report').read()[0]
        action['target'] = 'main'
        action['name'] = f'Báo cáo hiệu quả nguồn lực trong dự án Từ {self.date_from.strftime("%d/%m/%Y")} đến {self.date_to.strftime("%d/%m/%Y")}'
        action['display_name'] = f'Báo cáo hiệu quả nguồn lực trong dự án Từ {self.date_from.strftime("%d/%m/%Y")} đến {self.date_to.strftime("%d/%m/%Y")}'
        action['context'] = {'model': 'effective.resource.project.report',
                             'project_id': self.project_id.id,
                             'project_ids': self.project_ids.ids,
                             'state_ids': self.state_ids.ids,
                             'department_ids': self.department_ids.ids,
                             'employee_ids': self.employee_ids.ids,
                             'block_ids': self.block_ids.ids,
                             'date_from': self.date_from,
                             'date_to': self.date_to,
                             'id_popup': self.id,
                             'period': self.period,
                             'unit': self.unit}
        return action

class EffectiveProjectAccountReport(models.AbstractModel):
    _name = "effective.resource.project.report"
    _description = "Báo cáo hiệu quả nguồn lực trong dự án"
    _inherit = "account.report"

    # filter_date = {'mode': 'range', 'filter': 'this_year'}
    filter_date = None
    filter_all_entries = None
    filter_journals = None
    filter_analytic = None
    filter_unfold_all = None

    @api.model
    def _get_report_name(self):
        ctx = self._context
        unit = ctx.get('unit')
        return f'''
                     {self._description} Đơn vị       : {unit}<br/>
        '''

    def get_report_filename(self, options):
        """The name that will be used for the file when downloading pdf,xlsx,..."""
        date_start = fields.Date.from_string(options['date_from'])
        date_end = fields.Date.from_string(options['date_to'])
        if date_start and date_end:
            return f"Báo cáo hiệu quả nguồn lực trong dự án_{date_start.strftime('%d%m%Y')}_đến_{date_end.strftime('%d%m%Y')}"
        else:
            return 'Báo cáo hiệu quả nguồn lực trong dự án'

    def _get_reports_buttons(self, options):
        return [
            # {'name': _('PDF'), 'sequence': 1, 'action': 'print_pdf', 'file_export_type': _('PDF')},
            {'name': _('XLSX'), 'sequence': 2, 'action': 'print_xlsx', 'file_export_type': _('XLSX')},
            {'name': _('Chọn thông tin báo cáo'), 'sequence': 3, 'action': 'get_popup_report'},
        ]

    def get_popup_report(self, options):
        action = self.env['ir.actions.act_window']._for_xml_id('account_reports.effective_resource_project_report_wizard_act')
        action['res_id'] = options.get('id_popup')
        return action

    def _set_context(self, options):
        ctx = super()._set_context(options)
        unit = ctx.get('unit')
        project_id = ctx.get('project_id')
        if not unit:
            wizard = self.env['effective.resource.project.report.wizard'].search([('create_uid', '=', self.env.user.id)], order='id desc', limit=1)
            unit = wizard.unit
            project_id = wizard.project_id.id

        ctx['unit'] = unit
        ctx['project_id'] = project_id
        return ctx

    def _get_options(self, previous_options=None):
        res = super()._get_options(previous_options=previous_options)
        lst_key = ['employee_ids', 'project_id', 'project_ids', 'state_ids', 'department_ids', 'unit', 'block_ids', 'period', 'id_popup', 'date_from', 'date_to']
        for k in lst_key:
            if k in self._context:
                res[k] = self._context.get(k)
            else:
                res[k] = previous_options.get(k) if previous_options else False

        return res

    @api.model
    def _get_columns(self, options):
        columns_names = [
            {'name': 'Mã nhân viên', 'style': 'padding-left:8px;background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap; border:1px solid #000000'},
            {'name': 'Email nhân viên', 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Trung tâm quản lý', 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Dự án', 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Trung tâm dự án', 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Nguồn lực', 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Tổng dự án', 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Tổng lũy kế', 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
        ]
        ctx = self._context
        date_from = min(fields.Date.from_string(options['date_from']), fields.Date.from_string(options['date_to'])) + relativedelta(day=1)
        date_to = max(fields.Date.from_string(options['date_from']), fields.Date.from_string(options['date_to'])) + relativedelta(
            day=1) + relativedelta(months=1) + relativedelta(days=-1)
        datetime_from = datetime.combine(date_from, time.min)
        datetime_to = datetime.combine(date_to, time.max)

        for date_step in date_utils.date_range(datetime_from, datetime_to, relativedelta(months=1)):
            columns_names += [{'name': f'Tháng {date_step.strftime("%m/%Y")}',
                                 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'}]
        return [columns_names]

    @api.model
    def _get_lines(self, options, line_id=None):
        lines = []
        self = self.sudo()
        lg = self.env['res.lang']._lang_get(self.env.user.lang) or get_lang(self.env)
        ctx = self._context
        unit = options.get('unit')
        project_id = options.get('project_id')
        project_ids = options.get('project_ids')
        state_ids = options.get('state_ids')
        department_ids = options.get('department_ids')
        block_ids = options.get('block_ids')
        employee_ids = options.get('employee_ids')
        date_from = min(fields.Date.from_string(options['date_from']), fields.Date.from_string(options['date_to'])) + relativedelta(day=1)
        date_to = max(fields.Date.from_string(options['date_from']), fields.Date.from_string(options['date_to'])) + relativedelta(day=1) + relativedelta(months=1) + relativedelta(days=-1)

        ext_domain = []
        if project_id:
            ext_domain = [('order_id.project_id', '=', project_id)]
        if project_ids and not project_id:
            ext_domain = [('order_id.project_id', 'in', project_ids)]
        if state_ids and not project_id:
            ext_domain += [('order_id.project_id.stage_id', 'in', state_ids)]
        if department_ids:
            ext_domain += [('order_id.project_id.en_department_id', 'in', department_ids)]
        if block_ids:
            ext_domain += [('order_id.project_id.en_block_id', 'in', block_ids)]
        if employee_ids:
            records = self.env['en.resource.detail'].search(
                ext_domain + [('order_id.state', '=', 'approved'), ('employee_id', 'in', employee_ids),])
        else:
            records = self.env['en.resource.detail'].search(
                ext_domain + [('order_id.state', '=', 'approved'), ('employee_id', '!=', False),])

        background = '#FFFFFF'

        min_date_from = date_from
        max_date_to = date_to
        final_date_from = max([min_date_from, date_from]) + relativedelta(day=1)
        final_date_to = min([max_date_to, date_to]) + relativedelta(day=1) + relativedelta(months=1) + relativedelta(days=-1)
        datetime_from = datetime.combine(final_date_from, time.min)
        datetime_to = datetime.combine(final_date_to, time.max)

        with localcontext() as ctx:
            ctx.rounding = ROUND_HALF_UP
            for department_id in records.mapped('employee_id.department_id').sorted(lambda x: x.name):
                for employee in records.filtered(lambda x: x.employee_id.department_id == department_id).mapped('employee_id').sorted(lambda x: x.barcode or ' '):
                    for project in records.filtered(lambda x: x.employee_id == employee).mapped('order_id.project_id').sorted(lambda x: x.en_code):
                        if background == '#FFFFFF':
                            background = '#D8DAE0'
                        else:
                            background = '#FFFFFF'
                        # plan
                        columns = [
                            {'name': employee.work_email or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                            {'name': employee.department_id.display_name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                            {'name': project.en_code or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                            {'name': project.en_department_id.display_name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                            {'name': 'Plan', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                        ]

                        resources_employee_project = self.env['en.resource.detail'].search(
                            [('order_id.project_id', '=', project.id), ('order_id.state', '=', 'approved'),
                             ('employee_id', '=', employee.id),], order='date_start asc')
                        value_total_project = 0
                        for resource in resources_employee_project:
                            date_start = resource.date_start
                            date_end = resource.date_end
                            workrange_hours = self.env['en.technical.model'].convert_daterange_to_hours(employee, date_start, date_end) * resource.workload
                            if unit == 'MD':
                                value_total_project += workrange_hours / 8
                            elif unit == 'MM':
                                value_total_project += workrange_hours / 8 / resource.order_id.mm_rate if resource.order_id.mm_rate else 0
                            else:
                                value_total_project += workrange_hours
                        # columns += [{'name': f'{Decimal(value_total_project * 100).to_integral_value(rounding=ROUND_HALF_UP) / 100}' if value_total_project else '', 'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:nowrap;border:1px solid #000000'}]
                        columns += [{'name': f'{Decimal(str(value_total_project)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)}' if value_total_project else '', 'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:nowrap;border:1px solid #000000'}]
                        extra_columns_plan = []
                        total_value = 0
                        dict_value_plan_month = dict()
                        for date_step in date_utils.date_range(datetime_from, datetime_to, relativedelta(months=1)):
                            compared_from = max(date_step + relativedelta(day=1), datetime_from).date()
                            compared_to = min(date_step + relativedelta(months=1, day=1, days=-1), datetime_to).date()

                            resources = self.env['en.resource.detail'].search(
                                [('order_id.project_id', '=', project.id), ('order_id.state', '=', 'approved'),
                                 ('employee_id', '=', employee.id), '|',
                                 '&', ('date_start', '<=', compared_from), ('date_end', '>=', compared_from),
                                 '&', ('date_start', '>=', compared_from), ('date_start', '<=', compared_to)], order='date_start asc')
                            value = 0
                            for resource in resources:
                                date_start = max(compared_from, resource.date_start)
                                date_end = min(compared_to, resource.date_end)
                                workrange_hours = self.env['en.technical.model'].convert_daterange_to_hours(employee, date_start, date_end) * resource.workload
                                if unit == 'MD':
                                    value += workrange_hours / 8

                                elif unit == 'MM':
                                    value += workrange_hours / 8 / resource.order_id.mm_rate if resource.order_id.mm_rate else 0

                                else:
                                    value += workrange_hours
                            dict_value_plan_month.update({
                                date_step.date(): value
                            })
                            # extra_columns_plan += [{'name': f'{Decimal(value * 100).to_integral_value(rounding=ROUND_HALF_UP) / 100}' if value else '', 'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:nowrap;border:1px solid #000000'}]
                            extra_columns_plan += [{'name': f'{Decimal(str(value)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)}' if value else '', 'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:nowrap;border:1px solid #000000'}]
                        date_start_project = datetime.combine(project.date_start, time.min)
                        if date_start_project < datetime_to:
                            for date_step in date_utils.date_range(date_start_project, datetime_to, relativedelta(months=1)):
                                compared_from = max(date_step + relativedelta(day=1), date_start_project).date()
                                compared_to = min(date_step + relativedelta(months=1, day=1, days=-1), datetime_to).date()

                                resources = self.env['en.resource.detail'].search(
                                    [('order_id.project_id', '=', project.id), ('order_id.state', '=', 'approved'),
                                     ('employee_id', '=', employee.id), '|',
                                     '&', ('date_start', '<=', compared_from), ('date_end', '>=', compared_from),
                                     '&', ('date_start', '>=', compared_from), ('date_start', '<=', compared_to)], order='date_start asc')

                                for resource in resources:
                                    date_start = max(compared_from, resource.date_start)
                                    date_end = min(compared_to, resource.date_end)

                                    workrange_hours = self.env['en.technical.model'].convert_daterange_to_hours(employee, date_start, date_end) * resource.workload
                                    if unit == 'MD':
                                        total_value += workrange_hours / 8
                                    elif unit == 'MM':
                                        total_value += workrange_hours / 8 / resource.order_id.mm_rate if resource.order_id.mm_rate else 0
                                    else:
                                        total_value += workrange_hours

                        # columns += [{'name': f'{Decimal(total_value * 100).to_integral_value(rounding=ROUND_HALF_UP) / 100}' if total_value else '', 'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:nowrap;border:1px solid #000000'}]
                        columns += [{'name': f'{Decimal(str(total_value)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)}' if total_value else '', 'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:nowrap;border:1px solid #000000'}]
                        columns += extra_columns_plan
                        lines += [{
                            'id': f'project_{project.id}_employee_{employee.id}',
                            'name': employee.barcode or '',
                            'style': f'padding-left:8px;background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000',
                            'level': 1,
                            'columns': columns,
                        }]
                        #actual
                        columns_actual = [
                            {'name': employee.work_email or '',
                             'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                            {'name': employee.department_id.display_name or '',
                             'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                            {'name': project.en_code or '',
                             'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                            {'name': project.en_department_id.display_name or '',
                             'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                            {'name': 'Actual',
                             'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                        ]
                        columns_actual_month = []
                        total_actual = 0
                        for timesheet in project.timesheet_ids.filtered(lambda x: x.employee_id == employee):
                            if timesheet.en_state == 'approved':
                                if unit == 'MD':
                                    total_actual += timesheet.unit_amount / 8
                                elif unit == 'MM':
                                    total_actual += timesheet.unit_amount / 8 / project.mm_rate if project.mm_rate else 0
                                else:
                                    total_actual += timesheet.unit_amount
                            if timesheet.ot_state == 'approved':
                                if unit == 'MD':
                                    total_actual += timesheet.ot_time / 8
                                elif unit == 'MM':
                                    total_actual += timesheet.ot_time / 8 / project.mm_rate if project.mm_rate else 0
                                else:
                                    total_actual += timesheet.ot_time

                        # columns_actual += [{'name': f'{Decimal(total_actual * 100).to_integral_value(rounding=ROUND_HALF_UP) / 100}' if total_actual else '', 'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:nowrap;border:1px solid #000000'}]
                        columns_actual += [{'name': f'{Decimal(str(total_actual)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)}' if total_actual else '', 'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:nowrap;border:1px solid #000000'}]

                        total_com_actual = 0
                        dict_value_actual_month = dict()
                        for date_step in date_utils.date_range(datetime_from, datetime_to, relativedelta(months=1)):
                            compared_from = max(date_step + relativedelta(day=1), datetime_from).date()
                            compared_to = min(date_step + relativedelta(months=1, day=1, days=-1), datetime_to).date()
                            value_month = 0
                            timesheets = self.env['account.analytic.line'].search([
                                ('employee_id', '=', employee.id), ('project_id', '=', project.id), ('date', '!=', False),
                                ('date', '<=', compared_to), ('date', '>=', compared_from)
                            ])
                            for timesheet in timesheets:
                                if timesheet.en_state == 'approved':
                                    if unit == 'MD':
                                        value_month += timesheet.unit_amount / 8
                                    elif unit == 'MM':
                                        value_month += timesheet.unit_amount / 8 / project.mm_rate if project.mm_rate else 0
                                    else:
                                        value_month += timesheet.unit_amount
                                if timesheet.ot_state == 'approved':
                                    if unit == 'MD':
                                        value_month += timesheet.ot_time / 8
                                    elif unit == 'MM':
                                        value_month += timesheet.ot_time / 8 / project.mm_rate if project.mm_rate else 0
                                    else:
                                        value_month += timesheet.ot_time
                            dict_value_actual_month.update({
                                date_step.date(): value_month
                            })
                            # columns_actual_month += [{'name': f'{Decimal(value_month * 100).to_integral_value(rounding=ROUND_HALF_UP) / 100}' if value_month else '', 'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:nowrap;border:1px solid #000000'}]
                            columns_actual_month += [{'name': f'{Decimal(str(value_month)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)}' if value_month else '', 'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:nowrap;border:1px solid #000000'}]
                        if date_start_project < datetime_to:
                            for date_step in date_utils.date_range(date_start_project, datetime_to, relativedelta(months=1)):
                                compared_from = max(date_step + relativedelta(day=1), date_start_project).date()
                                compared_to = min(date_step + relativedelta(months=1, day=1, days=-1), datetime_to).date()
                                value_month = 0
                                timesheets_com = self.env['account.analytic.line'].search([
                                    ('employee_id', '=', employee.id), ('project_id', '=', project.id), ('date', '!=', False),
                                    ('date', '<=', compared_to), ('date', '>=', compared_from)
                                ])
                                for timesheet in timesheets_com:
                                    if timesheet.en_state == 'approved':
                                        if unit == 'MD':
                                            value_month += timesheet.unit_amount / 8
                                        elif unit == 'MM':
                                            value_month += timesheet.unit_amount / 8 / project.mm_rate if project.mm_rate else 0
                                        else:
                                            value_month += timesheet.unit_amount
                                    if timesheet.ot_state == 'approved':
                                        if unit == 'MD':
                                            value_month += timesheet.ot_time / 8
                                        elif unit == 'MM':
                                            value_month += timesheet.ot_time / 8 / project.mm_rate if project.mm_rate else 0
                                        else:
                                            value_month += timesheet.ot_time
                                total_com_actual += value_month

                        # columns_actual += [{'name': f'{Decimal(total_com_actual * 100).to_integral_value(rounding=ROUND_HALF_UP) / 100}' if total_com_actual else '', 'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:nowrap;border:1px solid #000000'}]
                        columns_actual += [{'name': f'{Decimal(str(total_com_actual)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)}' if total_com_actual else '', 'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:nowrap;border:1px solid #000000'}]
                        columns_actual += columns_actual_month
                        lines += [{
                            'id': f'project_{project.id}_employee_{employee.id}_actual',
                            'name': employee.barcode or '',
                            'style': f'padding-left:8px;background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000',
                            'level': 1,
                            'columns': columns_actual,
                        }]
                        # ratio
                        columns_ratio = [
                            {'name': employee.work_email or '',
                             'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                            {'name': employee.department_id.display_name or '',
                             'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                            {'name': project.en_code or '',
                             'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                            {'name': project.en_department_id.display_name or '',
                             'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                            {'name': 'Tỷ lệ',
                             'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                        ]

                        total_ratio_project = total_actual/value_total_project if value_total_project else 0
                        columns_ratio += [{'name': f'{Decimal(total_ratio_project * 10000).to_integral_value() / 100}%' if total_ratio_project else '', 'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:nowrap;border:1px solid #000000'}]

                        total_ratio_com = total_com_actual/total_value if total_value else 0
                        background_line = background

                        if (0.8 < total_ratio_com < 0.95) or (1.05 < total_ratio_com < 1.2):
                            background_line = '#FFFF00'
                        elif (0.5 < total_ratio_com < 0.8) or 1.2 < total_ratio_com < 1.5:
                            background_line = '#FF9933'
                        elif total_ratio_com < 0.5 or total_ratio_com > 1.5:
                            background_line = '#FF0000'

                        columns_ratio += [{'name': f'{Decimal(total_ratio_com * 10000).to_integral_value(rounding=ROUND_HALF_UP) / 100}%' if total_ratio_com else '', 'style': f'background-color:{background_line};vertical-align:middle;text-align:right; white-space:nowrap;border:1px solid #000000'}]

                        columns_ratio_month = []
                        for date_step in date_utils.date_range(datetime_from, datetime_to, relativedelta(months=1)):
                            value_month_actual = dict_value_actual_month.get(date_step.date(), 0)
                            value_month_actual = Decimal(value_month_actual * 100).to_integral_value(rounding=ROUND_HALF_UP)/100
                            value_month_plan = dict_value_plan_month.get(date_step.date(), 0)
                            value_month_plan = Decimal(value_month_plan * 100).to_integral_value(rounding=ROUND_HALF_UP)/100
                            ratio_month = value_month_actual / value_month_plan if value_month_plan else 0
                            ratio_month = Decimal(ratio_month * 10000).to_integral_value(rounding=ROUND_HALF_UP)/100
                            columns_ratio_month += [{'name': f'{ratio_month}%' if ratio_month else '', 'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:nowrap;border:1px solid #000000'}]
                        columns_ratio += columns_ratio_month
                        lines += [{
                            'id': f'project_{project.id}_employee_{employee.id}_ratio',
                            'name': employee.barcode or '',
                            'style': f'padding-left:8px;background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000',
                            'level': 1,
                            'columns': columns_ratio,
                        }]

        return lines
