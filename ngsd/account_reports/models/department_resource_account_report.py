from odoo import models, fields, api, _
from odoo.tools.misc import format_date, DEFAULT_SERVER_DATE_FORMAT
from datetime import timedelta, datetime, time, date
from odoo.tools import config, date_utils, get_lang, html2plaintext
from dateutil.relativedelta import relativedelta
from decimal import localcontext, Decimal, ROUND_HALF_UP
from pytz import timezone
import math
from collections import defaultdict


class DepartmentResourceAccountReportWizard(models.TransientModel):
    _name = "department.resource.account.report.wizard"
    _description = "Báo cáo trung tâm"

    department_ids = fields.Many2many('hr.department', string='Trung tâm', domain="[('id', 'in', domain_department_ids), ('is_support', '=', False), ('bod', '=', False), ('no_check_lender', '=', False)]")
    domain_department_ids = fields.Many2many('hr.department', compute='_compute_domain_department')
    user_id = fields.Many2one('res.users', default=lambda self: self.env.user)

    @api.depends('user_id')
    def _compute_domain_department(self):
        all_department = self.env.user.has_group('ngsd_base.group_tpvh,ngsd_base.group_tptc,ngsd_base.group_qal,ngsd_base.group_qam,ngsd_base.group_userhr,ngsd_base.group_td')
        all_blocks = self.env.user.has_group('ngsd_base.group_gdkv,ngsd_base.group_tk')
        only_department = self.env.user.has_group('ngsd_base.group_gdkndu,ngsd_base.group_tppmo')
        for rec in self:
            if all_department:
                rec.domain_department_ids = self.env['hr.department'].search([])
            elif all_blocks and only_department:
                rec.domain_department_ids = self.env['hr.department'].search(['|', ('block_id', '=', self.env.user.employee_ids.en_block_id.id), ('id', '=', self.env.user.employee_ids.department_id.id)])
            elif all_blocks:
                rec.domain_department_ids = self.env['hr.department'].search([('block_id', '=', self.env.user.employee_ids.en_block_id.id)])
            elif only_department:
                rec.domain_department_ids = [(4, self.env.user.employee_ids.department_id.id)]
            else:
                rec.domain_department_ids = False

    def do(self):
        self = self.sudo()
        action = self.env.ref('account_reports.action_department_resource_account_report').read()[0]
        action['target'] = 'main'
        action['context'] = {
            'model': 'department.resource.account.report',
            'department_ids': self.department_ids.ids
        }
        return action


class DepartmentResourceAccountReport(models.AbstractModel):
    _name = "department.resource.account.report"
    _description = "Báo cáo theo trung tâm"
    _inherit = "account.report"

    filter_date = {
        'mode': 'range',
        'filter': 'custom',
        'date_from': fields.Date.today().replace(day=1, month=4) if fields.Date.today() > fields.Date.today().replace(day=31, month=3) else fields.Date.today().replace(day=1, month=4) + relativedelta(years=-1),
        'date_to': fields.Date.today().replace(day=31, month=3) + relativedelta(years=1) if fields.Date.today() > fields.Date.today().replace(day=31, month=3) else fields.Date.today().replace(day=31, month=3)
    }
    filter_all_entries = None
    filter_journals = None
    filter_analytic = None
    filter_unfold_all = None
    filter_department = False

    @api.model
    def _get_columns(self, options):

        columns_names = [
            {'name': 'Trung tâm', 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;border:1px solid #000000;'},
            {'name': 'Chỉ số', 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;border:1px solid #000000;'},
        ]

        date_from = min(fields.Date.from_string(options['date']['date_from']), fields.Date.from_string(options['date']['date_to'])) + relativedelta(day=1)
        date_to = max(fields.Date.from_string(options['date']['date_from']), fields.Date.from_string(options['date']['date_to'])) + relativedelta(day=1) + relativedelta(months=1) + relativedelta(days=-1)
        datetime_from = datetime.combine(date_from, time.min)
        datetime_to = datetime.combine(date_to, time.max)
        for date_step in date_utils.date_range(datetime_from, datetime_to, relativedelta(months=1)):
            columns_names += [{'name': f'{date_step.strftime("%m/%Y")}', 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;'}]

        return [columns_names]

    @api.model
    def _get_report_name(self):
        return self._description

    def get_report_filename(self, options):
        """The name that will be used for the file when downloading pdf,xlsx,..."""
        date_start = fields.Date.from_string(options['date']['date_from'])
        date_end = fields.Date.from_string(options['date']['date_to'])
        if date_start and date_end:
            return f"Báo cáo theo trung tâm_{date_start.strftime('%d%m%Y')}_đến_{date_end.strftime('%d%m%Y')}"
        else:
            return 'Báo cáo theo trung tâm'

    def _get_reports_buttons(self, options):
        return [
            # {'name': _('PDF'), 'sequence': 1, 'action': 'print_pdf', 'file_export_type': _('PDF')},
            {'name': _('XLSX'), 'sequence': 2, 'action': 'print_xlsx', 'file_export_type': _('XLSX')},
        ]

    def _get_options(self, previous_options=None):
        res = super()._get_options(previous_options=previous_options)
        lst_key = ['department_ids']
        for k in lst_key:
            if k in self._context:
                res[k] = self._context.get(k)
            else:
                res[k] = previous_options.get(k) if previous_options else False
        return res

    @api.model
    def _get_lines(self, options, line_id=None):
        lines = []
        lg = self.env['res.lang']._lang_get(self.env.user.lang) or get_lang(self.env)
        if self.env.user.has_group('ngsd_base.group_td'):
            self = self.sudo()
        date_from = min(fields.Date.from_string(options['date']['date_from']), fields.Date.from_string(options['date']['date_to'])) + relativedelta(day=1)
        date_to = max(fields.Date.from_string(options['date']['date_from']), fields.Date.from_string(options['date']['date_to'])) + relativedelta(day=1) + relativedelta(months=1) + relativedelta(days=-1)
        datetime_from = datetime.combine(date_from, time.min)
        datetime_to = datetime.combine(date_to, time.max)
        all_department = self.env.user.has_group('ngsd_base.group_tpvh,ngsd_base.group_tptc,ngsd_base.group_qal,ngsd_base.group_qam,ngsd_base.group_userhr,ngsd_base.group_td')
        all_blocks = self.env.user.has_group('ngsd_base.group_gdkv,ngsd_base.group_tk')
        only_department = self.env.user.has_group('ngsd_base.group_gdkndu,ngsd_base.group_tppmo')
        domain = [('is_support', '=', False), ('bod', '=', False), ('no_check_lender', '=', False)]
        department_ids = options.get('department_ids')
        if department_ids:
            domain += [('id', 'in', department_ids)]
        else:
            if all_department:
                domain += []
            elif all_blocks and only_department:
                domain += ['|', ('block_id', '=', self.env.user.employee_ids.en_block_id.id), ('id', '=', self.env.user.employee_ids.department_id.id)]
            elif all_blocks:
                domain += [('block_id', '=', self.env.user.employee_ids.en_block_id.id)]
            elif only_department:
                domain += [('id', '=', self.env.user.employee_ids.department_id.id)]
        records = self.env['hr.department'].search(domain)
        employees = self.env['hr.employee'].search([('department_id', 'in', records.ids)])
        employees |= self.env['hr.employee'].search([('active', '=', False), ('department_id', 'in', records.ids), ('departure_date', '>', datetime_from)])
        resource_planning = self.env['en.resource.detail'].search([('employee_id.department_id.bod', '=', False), ('employee_id.department_id.no_check_lender', '=', False), ('employee_id.department_id.is_support', '=', False), '|', ('order_id.project_id.en_department_id', 'in', records.ids), ('order_id.project_id.en_project_type_id.is_presale', '=', True), ('order_id.state', '=', 'approved'), ('order_id.project_id.stage_id.en_state', 'in', ['draft', 'wait_for_execution', 'doing', 'complete'])])
        self = self.sudo().with_context(no_format=True)
        background = '#FFFFFF'
        with localcontext() as ctx:
            ctx.rounding = ROUND_HALF_UP
            for record in records:
                if background == '#FFFFFF':
                    background = '#D8DAE0'
                else:
                    background = '#FFFFFF'
                columns10 = [
                    {'name': 'Nguồn lực nội bộ', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                ]
                columns1 = [
                    {'name': 'Kế hoạch nguồn lực', 'style': f'background-color:{background};vertical-align:middle;font-weight:bold;text-align:left; white-space:nowrap;border:1px solid #000000'},
                ]
                columns2 = [
                    {'name': 'Nguồn lực có thể sử dụng', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                ]
                columns3 = [
                    {'name': 'Nguồn lực nội bộ cho dự án', 'style': f'background-color:{background};font-style:italic;vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                ]
                columns4 = [
                    {'name': 'Nguồn lực nội bộ cho mượn trong dự án', 'style': f'background-color:{background};font-style:italic;vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                ]
                columns5 = [
                    {'name': 'Nguồn lực Outsource cho dự án', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                ]
                columns6 = [
                    {'name': 'Nguồn lực ẩn cho dự án', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                ]
                columns13 = [
                    {'name': 'Nguồn lực chưa vào dự án', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                ]
                columns11 = [
                    {'name': 'Tỷ lệ sử dụng nguồn lực nội bộ', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                ]
                columns7 = [
                    {'name': 'Kế hoạch nguồn lực trong dự án', 'style': f'background-color:{background};vertical-align:middle;font-weight:bold;text-align:left; white-space:nowrap;border:1px solid #000000'},
                ]
                columns8 = [
                    {'name': 'Nguồn lực cho mượn', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                ]
                columns9 = [
                    {'name': 'Nguồn lực nội bộ đi mượn cho dự án', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                ]
                columns12 = [
                    {'name': 'Tỷ lệ nguồn lực nội bộ đáp ứng dự án', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                ]
                columns14 = [
                    {'name': 'Nguồn lực đi mượn', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                ]

                for date_step in date_utils.date_range(datetime_from, datetime_to, relativedelta(months=1)):
                    compared_from = max(date_step + relativedelta(day=1), datetime_from).date()
                    compared_to = min(date_step + relativedelta(months=1, day=1, days=-1), datetime_to).date()

                    l10 = 0
                    for employee in self.env['hr.employee'].search([('department_id', '=', record.id), ('en_type_id.en_internal', '=', True), '|', ('active', '=', True), '&', ('active', '=', False), ('departure_date', '>', compared_from)]):
                        x = self.env['en.technical.model'].convert_daterange_to_hours(employee, compared_from, compared_to) / 8
                        y = self.env['en.technical.model'].convert_daterange_to_count(employee, compared_from, compared_to, exclude_tech_type=['off', 'holiday'])
                        l10 += x / y if y else 0
                    columns10 += [
                        {'name': Decimal(l10 * 100).to_integral_value(rounding=ROUND_HALF_UP) / 100, 'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:nowrap;border:1px solid #000000'},
                    ]

                    l3 = 0
                    for line in self.env['en.resource.detail'].search([
                        ('order_id.project_id.en_department_id', '=', record.id), ('order_id.active', '=', True), ('order_id.state', '=', 'approved'),
                        ('employee_id.department_id', '=', record.id),  ('employee_id.en_type_id.en_internal', '=', True),
                        ('date_end', '>=', compared_from), ('date_start', '<=', compared_to),
                    ]):
                        x = self.env['en.technical.model'].convert_daterange_to_hours(line.employee_id, max(compared_from, line.date_start), min(compared_to, line.date_end)) * line.workload / 8
                        y = self.env['en.technical.model'].convert_daterange_to_count(line.employee_id, compared_from, compared_to, exclude_tech_type=['off', 'holiday'])
                        l3 += x / y if y else 0
                    columns3 += [
                        {'name': Decimal(l3 * 100).to_integral_value(rounding=ROUND_HALF_UP) / 100, 'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:nowrap;border:1px solid #000000'},
                    ]

                    l4 = 0
                    for line in self.env['en.resource.detail'].search([
                        ('order_id.project_id.en_department_id', '!=', record.id), ('order_id.active', '=', True), ('order_id.state', '=', 'approved'),
                        ('employee_id.department_id', '=', record.id),  ('employee_id.en_type_id.en_internal', '=', True),
                        ('order_id.project_id.en_state', '!=', 'cancel'),
                        ('date_end', '>=', compared_from), ('date_start', '<=', compared_to),
                    ]):
                        x = self.env['en.technical.model'].convert_daterange_to_hours(line.employee_id, max(compared_from, line.date_start), min(compared_to, line.date_end)) * line.workload / 8
                        y = self.env['en.technical.model'].convert_daterange_to_count(line.employee_id, compared_from, compared_to, exclude_tech_type=['off', 'holiday'])
                        l4 += x / y if y else 0
                    columns4 += [
                        {'name': Decimal(l4 * 100).to_integral_value(rounding=ROUND_HALF_UP) / 100, 'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:nowrap;border:1px solid #000000'},
                    ]

                    l5 = 0
                    for line in self.env['en.resource.detail'].search([
                        ('order_id.project_id.en_department_id', '=', record.id), ('order_id.active', '=', True), ('order_id.state', '=', 'approved'),
                        ('employee_id.department_id', '=', record.id),  ('employee_id.department_id.en_os', '=', True),
                        ('date_end', '>=', compared_from), ('date_start', '<=', compared_to),
                    ]):
                        x = self.env['en.technical.model'].convert_daterange_to_hours(line.employee_id, max(compared_from, line.date_start), min(compared_to, line.date_end)) * line.workload / 8
                        y = self.env['en.technical.model'].convert_daterange_to_count(line.employee_id, compared_from, compared_to, exclude_tech_type=['off', 'holiday'])
                        l5 += x / y if y else 0
                    columns5 += [
                        {'name': Decimal(l5 * 100).to_integral_value(rounding=ROUND_HALF_UP) / 100, 'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:nowrap;border:1px solid #000000'},
                    ]

                    l6 = 0
                    for line in self.env['en.resource.detail'].search([
                        ('order_id.project_id.en_department_id', '=', record.id), ('order_id.active', '=', True), ('order_id.state', '=', 'approved'),
                        ('employee_id.department_id', '=', record.id),  ('employee_id.en_type_id.is_hidden', '=', True),
                        ('date_end', '>=', compared_from), ('date_start', '<=', compared_to),
                    ]):
                        x = self.env['en.technical.model'].convert_daterange_to_hours(line.employee_id, max(compared_from, line.date_start), min(compared_to, line.date_end)) * line.workload / 8
                        y = self.env['en.technical.model'].convert_daterange_to_count(line.employee_id, compared_from, compared_to, exclude_tech_type=['off', 'holiday'])
                        l6 += x / y if y else 0

                    columns6 += [
                        {'name': Decimal(l6 * 100).to_integral_value(rounding=ROUND_HALF_UP) / 100, 'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:nowrap;border:1px solid #000000'},
                    ]

                    l1 = l3 + l4 + l5 + l6
                    columns1 += [
                        {'name': Decimal(l1 * 100).to_integral_value(rounding=ROUND_HALF_UP) / 100, 'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:nowrap;border:1px solid #000000'},
                    ]

                    d_by_employee = defaultdict(lambda: 0)
                    l8 = 0
                    for line_lender in self.env['en.department.resource'].search([('department_id', '=', record.id), ('employee_id.en_internal_ok', '=', True), ('date_start', '<=', compared_to), ('date_end', '>=', compared_from)]):
                        date_start_line = max(line_lender.date_start, compared_from)
                        date_end_line = min(line_lender.date_end, compared_to)
                        date_work_month = self.env['en.technical.model'].convert_daterange_to_count(line_lender.employee_id, compared_from, compared_to, exclude_tech_type=['off', 'holiday'])
                        date_work_employee = self.env['en.technical.model'].convert_daterange_to_count(line_lender.employee_id, date_start_line, date_end_line, exclude_tech_type=['off', 'holiday', 'not_work']) * line_lender.workload
                        l8 += date_work_employee / date_work_month if date_work_month else 0
                        d_by_employee[line_lender.employee_id.id] -= date_work_employee / date_work_month if date_work_month else 0
                    columns8 += [
                        {'name': Decimal(l8 * 100).to_integral_value(rounding=ROUND_HALF_UP) / 100, 'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:nowrap;border:1px solid #000000'},
                    ]

                    l14 = 0
                    for line_borrow in self.env['en.department.resource'].search([('borrow_department_id', '=', record.id), ('employee_id.en_internal_ok', '=', True), ('date_start', '<=', compared_to), ('date_end', '>=', compared_from)]):
                        date_start_line = max(line_borrow.date_start, compared_from)
                        date_end_line = min(line_borrow.date_end, compared_to)
                        date_work_month = self.env['en.technical.model'].convert_daterange_to_count(line_borrow.employee_id, compared_from, compared_to, exclude_tech_type=['off', 'holiday'])
                        date_work_employee = self.env['en.technical.model'].convert_daterange_to_count(line_borrow.employee_id, date_start_line, date_end_line, exclude_tech_type=['off', 'holiday', 'not_work']) * line_borrow.workload
                        l14 += date_work_employee / date_work_month if date_work_month else 0
                        d_by_employee[line_borrow.employee_id.id] += date_work_employee / date_work_month if date_work_month else 0
                    columns14 += [
                        {'name': Decimal(l14 * 100).to_integral_value(rounding=ROUND_HALF_UP) / 100, 'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:nowrap;border:1px solid #000000'},
                    ]

                    l2 = 0
                    for employee in employees.filtered(lambda x: x.department_id == record and x.en_internal_ok):
                        date_work_month = self.env['en.technical.model'].convert_daterange_to_count(employee, compared_from, compared_to, exclude_tech_type=['off', 'holiday'])
                        date_work_employee = self.env['en.technical.model'].convert_daterange_to_count(employee, compared_from, compared_to, exclude_tech_type=['off', 'holiday', 'not_work'])
                        l2 += date_work_employee / date_work_month if date_work_month else 0
                        d_by_employee[employee.id] += date_work_employee / date_work_month if date_work_month else 0
                    l2 += l14 - l8
                    columns2 += [
                        {'name': Decimal(l2 * 100).to_integral_value(rounding=ROUND_HALF_UP) / 100,'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:nowrap;border:1px solid #000000'},
                    ]

                    l13 = 0
                    used = 0
                    for resource in resource_planning.filtered(lambda x: x.employee_id.en_internal_ok and (x.order_id.project_id.en_department_id == record or record == x.employee_id.department_id and x.order_id.project_id.en_project_type_id.is_presale) and (x.date_start <= compared_from <= x.date_end or compared_from <= x.date_start <= compared_to)):
                        date_start_line = max(resource.date_start, compared_from)
                        date_end_line = min(resource.date_end, compared_to)
                        date_work_month = self.env['en.technical.model'].convert_daterange_to_count(resource.employee_id, compared_from, compared_to, exclude_tech_type=['off', 'holiday'])
                        date_work_employee = self.env['en.technical.model'].convert_daterange_to_count(resource.employee_id, date_start_line, date_end_line, exclude_tech_type=['off', 'holiday', 'not_work']) * resource.workload
                        used += date_work_employee / date_work_month if date_work_month else 0
                        d_by_employee[resource.employee_id.id] -= date_work_employee / date_work_month if date_work_month else 0
                    l13 += sum([x for x in d_by_employee.values() if x > 0.001])
                    columns13 += [
                        {'name': Decimal(l13 * 100).to_integral_value(rounding=ROUND_HALF_UP) / 100, 'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:nowrap;border:1px solid #000000'},
                    ]
                    l11 = (l2-l13) / l2 if l2 else 0
                    l11 = max(l11, 0)
                    columns11 += [
                        {'name': f'{Decimal(l11 * 10000).to_integral_value(rounding=ROUND_HALF_UP)/100}%', 'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:nowrap;border:1px solid #000000'},
                    ]

                    l9 = 0
                    for line in self.env['en.resource.detail'].search([
                        ('order_id.project_id.en_department_id', '=', record.id), ('order_id.active', '=', True), ('order_id.state', '=', 'approved'),
                        ('employee_id.department_id', '!=', record.id),  ('employee_id.en_type_id.is_hidden', '=', True),
                        ('date_end', '>=', compared_from), ('date_start', '<=', compared_to),
                    ]):
                        x = self.env['en.technical.model'].convert_daterange_to_hours(line.employee_id, max(compared_from, line.date_start), min(compared_to, line.date_end)) * line.workload / 8
                        y = self.env['en.technical.model'].convert_daterange_to_count(line.employee_id, compared_from, compared_to, exclude_tech_type=['off', 'holiday'])
                        l9 += x / y if y else 0
                    columns9 += [
                        {'name': Decimal(l9 * 100).to_integral_value(rounding=ROUND_HALF_UP) / 100, 'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:nowrap;border:1px solid #000000'},
                    ]

                    l7 = l3 + l5 + l6 + l9
                    columns7 += [
                        {'name': Decimal(l7 * 100).to_integral_value(rounding=ROUND_HALF_UP) / 100, 'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:nowrap;border:1px solid #000000'},
                    ]

                    l12 = l3 / l7 if l7 else 0
                    columns12 += [
                        {'name': f'{Decimal(l12 * 10000).to_integral_value(rounding=ROUND_HALF_UP)/100}%' if l7 else '', 'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:nowrap;border:1px solid #000000'},
                    ]
                lines += [
                    {
                        'id': 'department_10_%s' % record.id,
                        'name': record.display_name or '',
                        'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000',
                        'level': 1,
                        'columns': columns10,
                    },
                    {
                        'id': 'department_2_%s' % record.id,
                        'name': record.display_name or '',
                        'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000',
                        'level': 1,
                        'columns': columns2,
                    },
                    {
                        'id': 'department_8_%s' % record.id,
                        'name': record.display_name or '',
                        'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000',
                        'level': 1,
                        'columns': columns8,
                    },
                    {
                        'id': 'department_14_%s' % record.id,
                        'name': record.display_name or '',
                        'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000',
                        'level': 1,
                        'columns': columns14,
                    },
                    {
                        'id': 'department_13_%s' % record.id,
                        'name': record.display_name or '',
                        'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000',
                        'level': 1,
                        'columns': columns13,
                    },
                    {
                        'id': 'department_11_%s' % record.id,
                        'name': record.display_name or '',
                        'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000',
                        'level': 1,
                        'columns': columns11,
                    },
                    {
                        'id': 'department_12_%s' % record.id,
                        'name': record.display_name or '',
                        'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000',
                        'level': 1,
                        'columns': columns12,
                    },
                    {
                        'id': 'department_1_%s' % record.id,
                        'name': record.display_name or '',
                        'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000',
                        'level': 1,
                        'columns': columns1,
                    },
                    {
                        'id': 'department_7_%s' % record.id,
                        'name': record.display_name or '',
                        'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000',
                        'level': 1,
                        'columns': columns7,
                    },
                    {
                        'id': 'department_3_%s' % record.id,
                        'name': record.display_name or '',
                        'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000',
                        'level': 1,
                        'columns': columns3,
                    },
                    {
                        'id': 'department_5_%s' % record.id,
                        'name': record.display_name or '',
                        'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000',
                        'level': 1,
                        'columns': columns5,
                    },
                    {
                        'id': 'department_6_%s' % record.id,
                        'name': record.display_name or '',
                        'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000',
                        'level': 1,
                        'columns': columns6,
                    },
                    {
                        'id': 'department_9_%s' % record.id,
                        'name': record.display_name or '',
                        'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000',
                        'level': 1,
                        'columns': columns9,
                    },
                    {
                        'id': 'department_4_%s' % record.id,
                        'name': record.display_name or '',
                        'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000',
                        'level': 1,
                        'columns': columns4,
                    },
                ]
        return lines

    @api.model
    def _get_lines_report_api(self, options, line_id=None):
        lines = []
        date_from = min(fields.Date.from_string(options['date']['date_from']), fields.Date.from_string(options['date']['date_to'])) + relativedelta(day=1)
        date_to = max(fields.Date.from_string(options['date']['date_from']), fields.Date.from_string(options['date']['date_to'])) + relativedelta(day=1) + relativedelta(months=1) + relativedelta(days=-1)
        datetime_from = datetime.combine(date_from, time.min)
        datetime_to = datetime.combine(date_to, time.max)

        records = self.env['hr.department'].search([])
        with localcontext() as ctx:
            ctx.rounding = ROUND_HALF_UP
            for record in records:
                dict_columns = dict(
                    columns1='Kế hoạch nguồn lực', #ok
                    columns3='Nguồn lực nội bộ cho dự án', #ok
                    columns4='Nguồn lực nội bộ cho mượn', #ok
                    columns5='Nguồn lực Outsource cho dự án', #ok
                    columns6='Nguồn lực ẩn cho dự án', #ok
                    columns7='Kế hoạch nguồn lực trong dự án', #ok
                    columns13='Nguồn lực nội bộ rảnh rỗi',
                    columns9='Nguồn lực nội bộ đi mượn cho dự án', #ok
                    columns10='Nguồn lực nội bộ', #ok
                    columns11='Tỷ lệ sử dụng nguồn lực nội bộ', #ok
                    columns12='Tỷ lệ nguồn lực nội bộ đáp ứng dự án', #ok
                )
                criteria_api = self.env['table.criteria.api'].search([])
                for column in dict_columns:
                    mapped_column = criteria_api.filtered(lambda x: x.criteria_lv2 == dict_columns[column])
                    if mapped_column:
                        dict_columns[column] = mapped_column[:1].id
                    else:
                        dict_columns[column] = False
                department_id = record.id
                for date_step in date_utils.date_range(datetime_from, datetime_to, relativedelta(months=1)):
                    compared_from = max(date_step + relativedelta(day=1), datetime_from).date()
                    compared_to = min(date_step + relativedelta(months=1, day=1, days=-1), datetime_to).date()
                    month_text = compared_from.strftime('%m')
                    year_text = compared_from.strftime('%Y')
                    l1 = 0
                    # l2 = 0
                    l3 = 0
                    for project in self.env['project.project'].search([('en_department_id', '=', record.id)]):
                        resource = project.en_resource_id
                        for line in resource.order_line:
                            if line.date_end < compared_from: continue
                            if line.date_start > compared_to: continue
                            employee = line.employee_id
                            if not employee.department_id == record:continue
                            if not employee.en_type_id.en_internal: continue
                            x = self.env['en.technical.model'].convert_daterange_to_hours(line.employee_id,
                                                                                          max(compared_from, line.date_start),
                                                                                          min(compared_to,
                                                                                              line.date_end)) * line.workload / 8
                            y = self.env['en.technical.model'].convert_daterange_to_count(line.employee_id, compared_from, compared_to,
                                                                                          exclude_tech_type=['off', 'holiday'])
                            l3 += x / y if y else 0
                    lines.append({
                        'Trung tâm': department_id,
                        'Chỉ số': dict_columns.get('columns3'),
                        'Tháng': month_text,
                        'Năm': year_text,
                        'Ngày': f'01/{month_text}/{year_text}',
                        'Giá trị': Decimal(l3 * 10).to_integral_value(rounding=ROUND_HALF_UP) / 10
                    })

                    l4 = 0
                    for project in self.env['project.project'].search([('en_department_id', '!=', record.id)]):
                        resource = project.en_resource_id
                        if resource.state != 'approved': continue
                        for line in resource.order_line:
                            if line.date_end < compared_from: continue
                            if line.date_start > compared_to: continue
                            employee = line.employee_id
                            if not employee.department_id == record:continue
                            if not employee.en_type_id.en_internal: continue
                            x = self.env['en.technical.model'].convert_daterange_to_hours(line.employee_id,
                                                                                          max(compared_from, line.date_start),
                                                                                          min(compared_to,
                                                                                              line.date_end)) * line.workload / 8
                            y = self.env['en.technical.model'].convert_daterange_to_count(line.employee_id, compared_from, compared_to,
                                                                                          exclude_tech_type=['off', 'holiday'])
                            l4 += x / y if y else 0
                    lines.append({
                        'Trung tâm': department_id,
                        'Chỉ số': dict_columns.get('columns4'),
                        'Tháng': month_text,
                        'Năm': year_text,
                        'Ngày': f'01/{month_text}/{year_text}',
                        'Giá trị': Decimal(l4 * 10).to_integral_value(rounding=ROUND_HALF_UP) / 10
                    })

                    # l2 += l3 + l4
                    # lines.append({
                    #     'Trung tâm': department_id,
                    #     'Chỉ số': dict_columns.get('columns2'),
                    #     'Tháng': month_text,
                    #     'Năm': year_text,
                    #     'Ngày': f'1/{month_text}/{year_text}',
                    #     'Giá trị': Decimal(l2 * 10).to_integral_value(rounding=ROUND_HALF_UP) / 10
                    # })

                    l5 = 0
                    for project in self.env['project.project'].search([('en_department_id', '=', record.id)]):
                        resource = project.en_resource_id
                        for line in resource.order_line:
                            if line.date_end < compared_from: continue
                            if line.date_start > compared_to: continue
                            employee = line.employee_id
                            if not employee.department_id.en_os: continue
                            x = self.env['en.technical.model'].convert_daterange_to_hours(line.employee_id,
                                                                                          max(compared_from, line.date_start),
                                                                                          min(compared_to,
                                                                                              line.date_end)) * line.workload / 8
                            y = self.env['en.technical.model'].convert_daterange_to_count(line.employee_id, compared_from, compared_to,
                                                                                          exclude_tech_type=['off', 'holiday'])
                            l5 += x / y if y else 0
                    lines.append({
                        'Trung tâm': department_id,
                        'Chỉ số': dict_columns.get('columns5'),
                        'Tháng': month_text,
                        'Năm': year_text,
                        'Ngày': f'01/{month_text}/{year_text}',
                        'Giá trị': Decimal(l5 * 10).to_integral_value(rounding=ROUND_HALF_UP) / 10
                    })

                    l6 = 0
                    for employee in self.env['hr.employee'].search([('department_id', '=', record.id)]):
                        if not employee.en_type_id.is_hidden: continue
                        x = self.env['en.technical.model'].convert_daterange_to_hours(line.employee_id, max(compared_from, line.date_start),
                                                                                      min(compared_to, line.date_end)) * line.workload / 8
                        y = self.env['en.technical.model'].convert_daterange_to_count(line.employee_id, compared_from, compared_to,
                                                                                      exclude_tech_type=['off', 'holiday'])
                        l6 += x / y if y else 0
                    lines.append({
                        'Trung tâm': department_id,
                        'Chỉ số': dict_columns.get('columns6'),
                        'Tháng': month_text,
                        'Năm': year_text,
                        'Ngày': f'01/{month_text}/{year_text}',
                        'Giá trị': Decimal(l6 * 10).to_integral_value(rounding=ROUND_HALF_UP) / 10
                    })

                    l1 += l3 + l4 + l5 + l6
                    lines.append({
                        'Trung tâm': department_id,
                        'Chỉ số': dict_columns.get('columns1'),
                        'Tháng': month_text,
                        'Năm': year_text,
                        'Ngày': f'01/{month_text}/{year_text}',
                        'Giá trị': Decimal(l1 * 10).to_integral_value(rounding=ROUND_HALF_UP) / 10
                    })
                    l9 = 0
                    for line in self.env['en.resource.detail'].search([
                        ('order_id.project_id.en_department_id', '=', record.id), ('order_id.active', '=', True), ('order_id.state', '=', 'approved'),
                        ('employee_id.department_id', '!=', record.id),  ('employee_id.en_type_id.is_hidden', '=', True),
                        ('date_end', '>=', compared_from), ('date_start', '<=', compared_to),
                    ]):
                        x = self.env['en.technical.model'].convert_daterange_to_hours(line.employee_id, max(compared_from, line.date_start), min(compared_to, line.date_end)) * line.workload / 8
                        y = self.env['en.technical.model'].convert_daterange_to_count(line.employee_id, compared_from, compared_to, exclude_tech_type=['off', 'holiday'])
                        l9 += x / y if y else 0
                    lines.append({
                        'Trung tâm': department_id,
                        'Chỉ số': dict_columns.get('columns9'),
                        'Tháng': month_text,
                        'Năm': year_text,
                        'Ngày': f'01/{month_text}/{year_text}',
                        'Giá trị': Decimal(l9 * 10).to_integral_value(rounding=ROUND_HALF_UP) / 10
                    })
                    l7 = l3 + l5 + l6 + l9
                    lines.append({
                        'Trung tâm': department_id,
                        'Chỉ số': dict_columns.get('columns7'),
                        'Tháng': month_text,
                        'Năm': year_text,
                        'Ngày': f'01/{month_text}/{year_text}',
                        'Giá trị': Decimal(l7 * 10).to_integral_value(rounding=ROUND_HALF_UP) / 10
                    })

                    # l8 = l3 + l5 + l6
                    # lines.append({
                    #     'Trung tâm': department_id,
                    #     'Chỉ số': dict_columns.get('columns8'),
                    #     'Tháng': month_text,
                    #     'Năm': year_text,
                    #     'Ngày': f'01/{month_text}/{year_text}',
                    #     'Giá trị': Decimal(l8 * 10).to_integral_value(rounding=ROUND_HALF_UP) / 10
                    # })

                    l10 = 0
                    for employee in self.env['hr.employee'].search([('department_id', '=', record.id), ('en_type_id.en_internal', '=', True)]):
                        x = self.env['en.technical.model'].convert_daterange_to_hours(employee, compared_from,compared_to) / 8
                        y = self.env['en.technical.model'].convert_daterange_to_count(employee, compared_from, compared_to, exclude_tech_type=['off', 'holiday'])
                        l10 += x / y if y else 0
                        # x = 0
                        # y = 0
                        # tech_data = self.env['en.technical.model'].convert_daterange_to_data(employee, datetime.combine(compared_from, time.min), datetime.combine(compared_to, time.max))
                        # for d in tech_data:
                        #     tech = tech_data.get(d)
                        #     if tech and tech.get('tech') not in ['off', 'holiday']:
                        #         y += 1
                        #     if tech and tech.get('number'):
                        #         x += tech.get('number') / 8
                        # l10 += x / y
                    lines.append({
                        'Trung tâm': department_id,
                        'Chỉ số': dict_columns.get('columns10'),
                        'Tháng': month_text,
                        'Năm': year_text,
                        'Ngày': f'01/{month_text}/{year_text}',
                        'Giá trị': Decimal(l10 * 10).to_integral_value(rounding=ROUND_HALF_UP) / 10
                    })

                    l13 = 0
                    for employee in self.env['hr.employee'].search([('department_id', '=', record.id), ('en_type_id.en_internal', '=', True)]):
                        y = 0
                        z = 0
                        tech_data = self.env['en.technical.model'].convert_daterange_to_data(employee, compared_from, compared_to)
                        detail_data = self.env['en.resource.detail'].convert_daterange_to_data(employee, compared_from, compared_to)
                        for d in tech_data:
                            tech = tech_data.get(d)
                            if tech and tech.get('tech_type') not in ['off', 'holiday']:
                                y += 1
                            if tech and tech.get('tech_type') not in ['off', 'holiday', 'not_work', 'layoff']:
                                z += max(0, 1 - detail_data.get(d))
                        l13 += z / y if y else 0
                    lines.append({
                        'Trung tâm': department_id,
                        'Chỉ số': dict_columns.get('columns13'),
                        'Tháng': month_text,
                        'Năm': year_text,
                        'Ngày': f'01/{month_text}/{year_text}',
                        'Giá trị': Decimal(l13 * 10).to_integral_value(rounding=ROUND_HALF_UP) / 10,
                    })

                    l11 = (l10 - l13) / l10 if l10 else 0
                    lines.append({
                        'Trung tâm': department_id,
                        'Chỉ số': dict_columns.get('columns11'),
                        'Tháng': month_text,
                        'Năm': year_text,
                        'Ngày': f'01/{month_text}/{year_text}',
                        'Giá trị': Decimal(l11 * 10000).to_integral_value(rounding=ROUND_HALF_UP)/100
                    })

                    l12 = l3 / l7 if l7 else 0
                    lines.append({
                        'Trung tâm': department_id,
                        'Chỉ số': dict_columns.get('columns12'),
                        'Tháng': month_text,
                        'Năm': year_text,
                        'Ngày': f'01/{month_text}/{year_text}',
                        'Giá trị': Decimal(l12 * 10000).to_integral_value(rounding=ROUND_HALF_UP)/100
                    })
        return lines
