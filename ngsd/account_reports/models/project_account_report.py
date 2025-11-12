from odoo import models, fields, api, _
from odoo.tools.misc import format_date, DEFAULT_SERVER_DATE_FORMAT
from datetime import timedelta, datetime, time
from odoo.tools import config, date_utils, get_lang, html2plaintext
from dateutil.relativedelta import relativedelta
from decimal import localcontext, Decimal, ROUND_HALF_UP
from pytz import timezone
import math


class ProjectAccountReportWizard(models.TransientModel):
    _name = "project.account.report.wizard"
    _description = "Kế hoạch nguồn lực sử dụng trong dự án"

    def _default_state_ids(self):
        return self.env['project.project.stage'].search([('en_state', 'not in', ['complete', 'cancel'])]).ids

    project_id = fields.Many2one(string='Dự án', comodel_name='project.project')
    unit = fields.Selection(string='Đơn vị', selection=[('MM', 'MM'), ('MD', 'MD'), ('MH', 'MH')], default='MM', required=True)
    project_ids = fields.Many2many('project.project', string='Dự án', domain="['|', ('en_department_id', 'in', department_ids), ('en_block_id', 'in', block_ids)]")
    state_ids = fields.Many2many('project.project.stage', string="Trạng thái", default=lambda self: self._default_state_ids())
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
        action = self.env.ref('account_reports.action_project_account_report').read()[0]
        action['target'] = 'main'
        action['name'] = f'Kế hoạch nguồn lực Từ {self.date_from.strftime("%d/%m/%Y")} đến {self.date_to.strftime("%d/%m/%Y")}'
        action['display_name'] = f'Kế hoạch nguồn lực Từ {self.date_from.strftime("%d/%m/%Y")} đến {self.date_to.strftime("%d/%m/%Y")}'
        action['context'] = {'model': 'project.account.report',
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


class ProjectAccountReport(models.AbstractModel):
    _name = "project.account.report"
    _description = "Kế hoạch nguồn lực sử dụng trong dự án"
    _inherit = "account.report"

    # filter_date = {'mode': 'range', 'filter': 'this_year'}
    filter_date = None
    filter_all_entries = None
    filter_journals = None
    filter_analytic = None
    filter_unfold_all = None

    @api.model
    def _get_columns(self, options):
        columns_names = [
            {'name': 'Thông tin dự án', 'colspan': 3, 'style': 'padding-left:8px;background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap; border:1px solid #000000'},
            {'name': 'Thông tin nhân sự', 'colspan': 6, 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Tổ chức dự án', 'colspan': 2, 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
        ]
        columns_monthly = [
            {'name': 'Mã dự án', 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Trạng thái',
             'style': 'padding-left:8px;background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap; border:1px solid #000000'},
            {'name': 'Trung tâm', 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Loại', 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Tên nhân viên', 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Trung tâm', 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Email', 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Chức danh', 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Cấp bậc', 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Vai trò', 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Vị trí', 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Tổng', 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
        ]
        ctx = self._context
        date_from = min(fields.Date.from_string(options['date_from']), fields.Date.from_string(options['date_to'])) + relativedelta(day=1)
        date_to = max(fields.Date.from_string(options['date_from']), fields.Date.from_string(options['date_to'])) + relativedelta(day=1) + relativedelta(months=1) + relativedelta(days=-1)
        datetime_from = datetime.combine(date_from, time.min)
        datetime_to = datetime.combine(date_to, time.max)
        final_date_from = date_from
        final_date_to = date_to
        x = 0
        for date_step in date_utils.date_range(datetime_from, datetime_to, relativedelta(months=1)):
            x += 1
            columns_monthly += [{'pre-offset': 11 + x, 'name': f'{date_step.strftime("%m/%Y")}', 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'}]
        columns_names += [{'name': 'Kế hoạch Nguồn lực sử dụng trong dự án', 'colspan': 1 + x, 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'}]
        return [columns_names, columns_monthly]

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
            return f"Báo cáo kế hoạch nguồn lực_{date_start.strftime('%d%m%Y')}_đến_{date_end.strftime('%d%m%Y')}"
        else:
            return 'Báo cáo kế hoạch nguồn lực'

    def _get_reports_buttons(self, options):
        return [
            # {'name': _('PDF'), 'sequence': 1, 'action': 'print_pdf', 'file_export_type': _('PDF')},
            {'name': _('XLSX'), 'sequence': 2, 'action': 'print_xlsx', 'file_export_type': _('XLSX')},
            {'name': _('Chọn thông tin báo cáo KHNL'), 'sequence': 3, 'action': 'get_popup_report'},
        ]

    def get_popup_report(self, options):
        action = self.env['ir.actions.act_window']._for_xml_id('account_reports.project_account_report_wizard_act')
        action['res_id'] = options.get('id_popup')
        return action

    def _set_context(self, options):
        ctx = super()._set_context(options)
        unit = ctx.get('unit')
        project_id = ctx.get('project_id')
        if not unit:
            wizard = self.env['project.account.report.wizard'].search([('create_uid', '=', self.env.user.id)], order='id desc', limit=1)
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
            # if k in ['date_from', 'date_to'] and not self._context.get(k) and previous_options.get('date'):
            #     res[k] = previous_options.get('date')[k]
        return res

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
                ext_domain + [('order_id.state', '=', 'approved'), ('employee_id', 'in', employee_ids), '|',
                              '&', ('date_start', '<=', date_from), ('date_end', '>=', date_from),
                              '&', ('date_start', '>=', date_from), ('date_start', '<=', date_to), ])
        else:
            records = self.env['en.resource.detail'].search(ext_domain + [('order_id.state', '=', 'approved'), ('employee_id', '!=', False), '|',
                                                                          '&', ('date_start', '<=', date_from), ('date_end', '>=', date_from),
                                                                          '&', ('date_start', '>=', date_from), ('date_start', '<=', date_to), ])

        background = '#FFFFFF'

        min_date_from = date_from
        max_date_to = date_to
        final_date_from = max([min_date_from, date_from]) + relativedelta(day=1)
        final_date_to = min([max_date_to, date_to]) + relativedelta(day=1) + relativedelta(months=1) + relativedelta(days=-1)

        datetime_from = datetime.combine(final_date_from, time.min)
        datetime_to = datetime.combine(final_date_to, time.max)

        with localcontext() as ctx:
            ctx.rounding = ROUND_HALF_UP
            for project in records.mapped('order_id.project_id').sorted(lambda x: x.en_code.lower()):
                if background == '#FFFFFF':
                    background = '#D8DAE0'
                else:
                    background = '#FFFFFF'
                total_value_project = 0
                columns_month_total = []
                total_resources = self.env['en.resource.detail']
                for date_step in date_utils.date_range(datetime_from, datetime_to, relativedelta(months=1)):
                    compared_from = max(date_step + relativedelta(day=1), datetime_from).date()
                    compared_to = min(date_step + relativedelta(months=1, day=1, days=-1), datetime_to).date()
                    value_total_month = 0
                    for employee in records.filtered(lambda x: x.order_id.project_id == project).mapped('employee_id'):
                        resources = self.env['en.resource.detail'].search(
                            [('order_id.project_id', '=', project.id), ('order_id.state', '=', 'approved'),
                             ('employee_id', '=', employee.id), '|',
                             '&', ('date_start', '<=', compared_from), ('date_end', '>=', compared_from),
                             '&', ('date_start', '>=', compared_from), ('date_start', '<=', compared_to)],
                            order='date_start asc')
                        total_resources |= resources

                        for resource in resources:
                            date_start = max(compared_from, resource.date_start)
                            date_end = min(compared_to, resource.date_end)

                            workrange_hours = self.env['en.technical.model'].convert_daterange_to_hours(employee, date_start, date_end) * resource.workload
                            if unit == 'MD':
                                value_total_month += (workrange_hours / 8) * 100
                            elif unit == 'MM':
                                value_total_month += (workrange_hours / 8 / resource.order_id.mm_rate) * 100 if resource.order_id.mm_rate else 0
                            else:
                                value_total_month += workrange_hours * 100
                    columns_month_total += [{'name': f'{Decimal(str(value_total_month/100)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)}',
                                             'style': f'background-color:{background};vertical-align:middle;font-weight: bold;text-align:left; white-space:nowrap;border:1px solid #000000'}, ]
                if unit == 'MD':
                    total_value_project += sum([resource.en_md for resource in total_resources]) * 100
                elif unit == 'MH':
                    total_value_project += sum([resource.en_md * 8 for resource in total_resources]) * 100
                else:
                    total_value_project += sum([resource.en_md/resource.order_id.mm_rate if resource.order_id.mm_rate else 0 for resource in total_resources]) * 100

                columns_total = [
                    {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    {'name': f'{Decimal(str(total_value_project/100)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)}',
                     'style': f'background-color:{background};vertical-align:middle;text-align:left;font-weight:bold;white-space:nowrap;border:1px solid #000000'},
                ]
                columns_total += columns_month_total
                lines += [{
                    'id': project.id,
                    'name': project.en_code or '',
                    'style': f'padding-left:8px;background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000',
                    'level': 1,
                    'columns': columns_total,
                    'unfoldable': True,
                    'unfolded': True,

                }]
                for employee in records.filtered(lambda x: x.order_id.project_id == project).mapped('employee_id').sorted(lambda x: x.name.lower()):
                    if background == '#FFFFFF':
                        background = '#D8DAE0'
                    else:
                        background = '#FFFFFF'

                    columns = [
                        {'name': project.stage_id.display_name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                        {'name': project.en_department_id.display_name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                        {'name': employee.en_type_id.display_name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                        {'name': employee.name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                        {'name': employee.department_id.display_name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                        {'name': employee.work_email or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                        {'name': employee.job_id.display_name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                        {'name': employee.en_level_id.display_name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                        {'name': ', '.join(records.filtered(lambda x: x.order_id.project_id == project and x.employee_id == employee).mapped('role_id.display_name')), 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                        {'name': ', '.join(records.filtered(lambda x: x.order_id.project_id == project and x.employee_id == employee).mapped('job_position_id.display_name')), 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    ]

                    calendar = employee.resource_calendar_id
                    extra_columns = []
                    total_resources = self.env['en.resource.detail']
                    for date_step in date_utils.date_range(datetime_from, datetime_to, relativedelta(months=1)):
                        compared_from = max(date_step + relativedelta(day=1), datetime_from).date()
                        compared_to = min(date_step + relativedelta(months=1, day=1, days=-1), datetime_to).date()

                        resources = self.env['en.resource.detail'].search([('order_id.project_id', '=', project.id), ('order_id.state', '=', 'approved'), ('employee_id', '=', employee.id), '|',
                                                                           '&', ('date_start', '<=', compared_from), ('date_end', '>=', compared_from),
                                                                           '&', ('date_start', '>=', compared_from), ('date_start', '<=', compared_to)], order='date_start asc')
                        value = 0
                        for resource in resources:
                            date_start = max(compared_from, resource.date_start)
                            date_end = min(compared_to, resource.date_end)

                            workrange_hours = self.env['en.technical.model'].convert_daterange_to_hours(employee, date_start, date_end) * resource.workload
                            if unit == 'MD':
                                value += (workrange_hours / 8) * 100
                            elif unit == 'MM':
                                value += (workrange_hours / 8 / resource.order_id.mm_rate) * 100 if resource.order_id.mm_rate else 0
                            else:
                                value += workrange_hours * 100
                        total_resources |= resources
                        extra_columns += [{'name': f'{Decimal(str(value/100)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)}' if value else '', 'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:nowrap;border:1px solid #000000'}]
                    if unit == 'MD':
                        total_value = sum([resource.en_md for resource in total_resources]) * 100
                    elif unit == 'MH':
                        total_value = sum([resource.en_md * 8 for resource in total_resources]) * 100
                    else:
                        total_value = sum([resource.en_md/resource.order_id.mm_rate if resource.order_id.mm_rate else 0 for resource in total_resources]) * 100
                    columns += [{'name': f'{Decimal(str(total_value/100)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)}' if total_value else '', 'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:nowrap;border:1px solid #000000'}]
                    columns += extra_columns
                    lines += [{
                        'id': f'project_{project.id}_employee_{employee.id}',
                        'name': project.en_code or '',
                        'style': f'padding-left:8px;background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000',
                        'level': 3,
                        'columns': columns,
                        'parent_id': project.id,
                    }]
        return lines
