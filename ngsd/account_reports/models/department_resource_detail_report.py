from odoo import models, fields, api, _
from odoo.tools.misc import format_date, DEFAULT_SERVER_DATE_FORMAT
from datetime import timedelta, datetime, time
from odoo.tools import config, date_utils, get_lang, html2plaintext
from dateutil.relativedelta import relativedelta
from decimal import localcontext, Decimal, ROUND_HALF_UP
from pytz import timezone
import math
def daterange(start_date, end_date):
    for n in range(int(((end_date + timedelta(days=1)) - start_date).days)):
        yield start_date + timedelta(n)


class DepartmentResourceDetailReportWizard(models.TransientModel):
    _name = "department.resource.detail.wizard"
    _description = "Báo cáo nguồn lực chi tiết của TT"

    employee_ids = fields.Many2many(string='Nhân viên', comodel_name='hr.employee')
    department_ids = fields.Many2many('hr.department', string='Trung tâm', domain="[('id', 'in', department_domain)]")
    department_domain = fields.Many2many('hr.department', compute='_compute_domain_department')
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
    user_id = fields.Many2one('res.users', default=lambda self: self.env.user)

    @api.onchange('department_ids')
    def _onchange_department(self):
        for rec in self:
            rec.employee_ids = False

    @api.depends('user_id')
    def _compute_domain_department(self):
        all_department = self.env.user.has_group('ngsd_base.group_tpvh,ngsd_base.group_tptc,ngsd_base.group_qal,ngsd_base.group_qam,ngsd_base.group_userhr,ngsd_base.group_td')
        all_blocks = self.env.user.has_group('ngsd_base.group_gdkv,ngsd_base.group_tk')
        only_department = self.env.user.has_group('ngsd_base.group_gdkndu,ngsd_base.group_tppmo')
        domain = [('is_support', '=', False), ('bod', '=', False), ('no_check_lender', '=', False)]
        for rec in self:
            if all_department:
                rec.department_domain = self.env['hr.department'].search(domain)
            elif all_blocks and only_department:
                rec.department_domain = self.env['hr.department'].search(domain + ['|', ('block_id', '=', self.env.user.employee_ids.en_block_id.id), ('id', '=', self.env.user.employee_ids.department_id.id)])
            elif all_blocks:
                rec.department_domain = self.env['hr.department'].search(domain + [('block_id', '=', self.env.user.employee_ids.en_block_id.id)])
            elif only_department:
                rec.department_domain = [(4, self.env.user.employee_ids.department_id.id)]
            else:
                rec.department_domain = False

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
        action = self.env.ref('account_reports.action_department_resource_detail_report').read()[0]
        action['target'] = 'main'
        action['name'] = f'Báo cáo nguồn lực chi tiết theo TT Từ {self.date_from.strftime("%d/%m/%Y")} đến {self.date_to.strftime("%d/%m/%Y")}'
        action['display_name'] = f'Báo cáo nguồn lực chi tiết theo TT Từ {self.date_from.strftime("%d/%m/%Y")} đến {self.date_to.strftime("%d/%m/%Y")}'
        action['context'] = {'model': 'department.resource.detail.report',
                             'employee_ids': self.employee_ids.ids,
                             'department_ids': self.department_ids.ids,
                             'block_ids': self.block_ids.ids,
                             'date_from': self.date_from,
                             'date_to': self.date_to,
                             'id_popup': self.id,
                             'period': self.period,
                             }
        return action


class DepartmentResourceDetailReport(models.AbstractModel):
    _name = "department.resource.detail.report"
    _description = "Báo cáo nguồn lực chi tiết của TT"
    _inherit = "account.report"

    # filter_date = {'mode': 'range', 'filter': 'this_year'}
    filter_all_entries = None
    filter_journals = None
    filter_analytic = None
    filter_unfold_all = False

    @api.model
    def _get_columns(self, options):
        columns_monthly = []
        columns_details = []
        date_from = min(fields.Date.from_string(options['date_from']), fields.Date.from_string(options['date_to'])) + relativedelta(day=1)
        date_to = max(fields.Date.from_string(options['date_from']), fields.Date.from_string(options['date_to'])) + relativedelta(day=1) + relativedelta(months=1) + relativedelta(days=-1)
        datetime_from = datetime.combine(date_from, time.min)
        datetime_to = datetime.combine(date_to, time.max)
        x = 0
        z = 15
        y1 = 0
        y2 = 0
        for date_step in date_utils.date_range(datetime_from, datetime_to, relativedelta(months=1)):
            x += 1
            z += 1
            columns_monthly += [{'pre-offset': z, 'name': f'{date_step.strftime("%m/%Y")}', 'rowspan': 2, 'style': 'padding-left:8px;background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap; border:1px solid #000000'}]
        for date_step in date_utils.date_range(datetime_from, datetime_to, relativedelta(months=1)):
            x += 1
            columns_monthly += [{'pre-offset': z + 1, 'name': f'{date_step.strftime("%m/%Y")}', 'colspan': 2, 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'}]
            columns_details += [
                {'pre-offset': z + 1, 'name': 'Mã dự án', 'style': 'padding-left:8px;background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap; border:1px solid #000000'},
                {'pre-offset': z + 2, 'name': f'MM', 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            ]
            z += 2
            y1 += 2
        for date_step in date_utils.date_range(datetime_from, datetime_to, relativedelta(months=1)):
            x += 1
            columns_monthly += [{'pre-offset': z + 1, 'name': f'{date_step.strftime("%m/%Y")}', 'colspan': 2, 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'}]
            columns_details += [
                {'pre-offset': z + 1, 'name': 'Mã dự án', 'style': 'padding-left:8px;background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap; border:1px solid #000000'},
                {'pre-offset': z + 2, 'name': f'MM', 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            ]
            z += 2
            y2 += 2
        for date_step in date_utils.date_range(datetime_from, datetime_to, relativedelta(months=1)):
            x += 1
            z += 1
            columns_monthly += [{'pre-offset': z, 'rowspan': 2, 'name': f'{date_step.strftime("%m/%Y")}', 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'}]

        columns_names = [
            {'name': 'Mã nhân sự', 'rowspan': 3, 'style': 'padding-left:8px;background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap; border:1px solid #000000'},
            {'name': 'Level', 'rowspan': 3, 'style': 'min-width:25px;background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap; border:1px solid #000000'},
            {'name': 'Loại', 'rowspan': 3, 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap; border:1px solid #000000'},
            {'name': 'Tên nhân sự', 'rowspan': 3, 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Email', 'rowspan': 3, 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Khu vực', 'rowspan': 3, 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Khối', 'rowspan': 3, 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Trung tâm', 'rowspan': 3, 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Phòng', 'rowspan': 3, 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Chức danh', 'rowspan': 3, 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Cấp bậc', 'rowspan': 3, 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Kỹ năng', 'rowspan': 3, 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Trạng thái', 'rowspan': 3, 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Trung tâm đang HĐ', 'rowspan': 3, 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Ngày bắt đầu', 'rowspan': 3, 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Ngày kết thúc', 'rowspan': 3, 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Nguồn lực có thể sử dụng', 'colspan': int(x/4), 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Nguồn lực trong dự án', 'colspan': y1, 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Nguồn lực kế hoạch sử dụng trong Opp', 'colspan': y2, 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Nguồn lực chưa vào dự án', 'colspan': int(x / 4), 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'}
        ]

        return [columns_names, columns_monthly, columns_details]

    @api.model
    def _get_report_name(self):
        ctx = self._context
        unit = ctx.get('unit')
        return f'''Báo cáo nguồn lực chi tiết theo TT
        '''

    def get_report_filename(self, options):
        """The name that will be used for the file when downloading pdf,xlsx,..."""
        date_start = fields.Date.from_string(options['date_from'])
        date_end = fields.Date.from_string(options['date_to'])
        if date_end and date_start:
            return f"Báo cáo Nguồn lực chi tiết của TT_{date_start.strftime('%d%m%Y')}_đến_{date_end.strftime('%d%m%Y')}"
        else:
            return 'Báo cáo Nguồn lực chi tiết của TT'

    def _get_reports_buttons(self, options):
        return [
            # {'name': _('PDF'), 'sequence': 1, 'action': 'print_pdf', 'file_export_type': _('PDF')},
            {'name': _('XLSX'), 'sequence': 2, 'action': 'print_xlsx', 'file_export_type': _('XLSX')},
            {'name': _('Chọn thông tin báo cáo'), 'sequence': 3, 'action': 'get_popup_report'},
        ]

    def get_popup_report(self, options):
        action = self.env['ir.actions.act_window']._for_xml_id('account_reports.department_resource_detail_wizard_act')
        action['res_id'] = options.get('id_popup')
        return action

    # def _set_context(self, options):
    #     ctx = super()._set_context(options)
    #     project_id = ctx.get('project_id')
    #     if not unit:
    #         wizard = self.env['effective.resource.project.report.wizard'].search([('create_uid', '=', self.env.user.id)], order='id desc', limit=1)
    #         project_id = wizard.project_id.id
    #
    #
    #     ctx['project_id'] = project_id
    #     return ctx


    def _get_options(self, previous_options=None):
        res = super()._get_options(previous_options=previous_options)
        lst_key = ['employee_ids', 'department_ids', 'period', 'id_popup', 'date_from', 'date_to', 'block_ids']
        for k in lst_key:
            if k in self._context:
                res[k] = self._context.get(k)
            else:
                res[k] = previous_options.get(k) if previous_options else False
        return res

    @api.model
    def _get_lines(self, options, line_id=None):
        lines = []
        self = self.sudo()
        lg = self.env['res.lang']._lang_get(self.env.user.lang) or get_lang(self.env)

        date_from = min(fields.Date.from_string(options['date_from']), fields.Date.from_string(options['date_to'])) + relativedelta(day=1)
        date_to = max(fields.Date.from_string(options['date_from']), fields.Date.from_string(options['date_to'])) + relativedelta(day=1) + relativedelta(months=1) + relativedelta(days=-1)
        datetime_from = datetime.combine(date_from, time.min)
        datetime_to = datetime.combine(date_to, time.max)

        employee_ids = options.get('employee_ids')

        all_department = self.env.user.has_group('ngsd_base.group_tpvh,ngsd_base.group_tptc,ngsd_base.group_qal,ngsd_base.group_qam,ngsd_base.group_userhr,ngsd_base.group_td')
        all_blocks = self.env.user.has_group('ngsd_base.group_gdkv,ngsd_base.group_tk')
        only_department = self.env.user.has_group('ngsd_base.group_gdkndu,ngsd_base.group_tppmo')
        domain_department = [('is_support', '=', False), ('bod', '=', False), ('no_check_lender', '=', False)]
        department_ids = options.get('department_ids')
        if department_ids:
            domain_department += [('id', 'in', department_ids)]
        else:
            if all_department:
                domain_department += []
            elif all_blocks and only_department:
                domain_department += ['|', ('block_id', '=', self.env.user.employee_ids.en_block_id.id), ('id', '=', self.env.user.employee_ids.department_id.id)]
            elif all_blocks:
                domain_department += [('block_id', '=', self.env.user.employee_ids.en_block_id.id)]
            elif only_department:
                domain_department += [('id', '=', self.env.user.employee_ids.department_id.id)]
        department_ids = self.env['hr.department'].search(domain_department).ids

        block_ids = options.get('block_ids')
        domain_time = [('is_hidden', '=', False), ('en_internal_ok', '=', True), '|', ('departure_date', '=', False), ('departure_date', '>=', date_from)]
        if employee_ids or department_ids:
            domain = []
            if employee_ids:
                domain += [('id', 'in', employee_ids)]
            if department_ids:
                domain += [('department_id', 'in', department_ids)]
            if block_ids:
                domain += [('en_block_id', 'in', block_ids)]

            employees = self.env['hr.employee'].search(domain + domain_time, order='name')
        else:
            employees = self.env['hr.employee'].search(domain_time, order='name')
        resource_planning_ids = self.env['en.resource.detail'].search([
            ('employee_id', 'in', employees.ids), ('order_id.state', '=', 'approved'),
            '|', '&', ('date_start', '<=', date_from), ('date_end', '>=', date_from), '&', ('date_start', '>=', date_from), ('date_start', '<=', date_to),
        ])
        background = '#FFFFFF'
        with localcontext() as ctx:
            ctx.rounding = ROUND_HALF_UP
            for employee in employees.sorted(lambda x: x.department_id.display_name or ' '):
                department_id = employee.department_id
                resource_employee = resource_planning_ids.filtered(lambda x: x.employee_id == employee)
                if background == '#FFFFFF':
                    background = '#D8DAE0'
                else:
                    background = '#FFFFFF'
                columns = [
                    {'name': '1', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    {'name': employee.en_type_id.display_name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    {'name': employee.name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    {'name': employee.work_email or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    {'name': employee.en_area_id.display_name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    {'name': employee.en_block_id.display_name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    {'name': employee.department_id.display_name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    {'name': employee.en_department_id.display_name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    {'name': employee.job_id.display_name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    {'name': employee.en_level_id.display_name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    {'name': employee.en_technique or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    {'name': dict(employee.fields_get(['en_status'])['en_status']['selection'])[employee.en_status] if employee.en_status else '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    {'name': employee.department_id.display_name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    {'name': employee.en_date_start.strftime(lg.date_format) if employee.en_date_start else '', 'class': 'date', 'style': f'background-color:{background};text-align:left;vertical-align:middle; white-space:nowrap;border:1px solid #000000;'},
                    {'name': employee.departure_date.strftime(lg.date_format) if employee.departure_date else '', 'class': 'date', 'style': f'background-color:{background};text-align:left;vertical-align:middle; white-space:nowrap;border:1px solid #000000;'},
                ]
                columns_total = []
                columns_project = []
                columns_opp = []
                columns_remain = []
                for date_step in date_utils.date_range(datetime_from, datetime_to, relativedelta(months=1)):
                    compared_from = max(date_step + relativedelta(day=1), datetime_from).date()
                    compared_to = min(date_step + relativedelta(months=1, day=1, days=-1), datetime_to).date()
                    date_work_month = self.env['en.technical.model'].convert_daterange_to_count(employee, compared_from, compared_to, exclude_tech_type=['off', 'holiday'])
                    date_work_lender = 0
                    for line in department_id.employee_lender_report_ids.filtered(lambda x: x.employee_id == employee):
                        date_start_line = max(line.date_start, compared_from)
                        date_end_line = min(line.date_end, compared_to)
                        date_work_lender += self.env['en.technical.model'].convert_daterange_to_count(employee, date_start_line, date_end_line) * line.workload
                    date_work_real = self.env['en.technical.model'].convert_daterange_to_count(employee, compared_from, compared_to)
                    mm_month_total = (date_work_real - date_work_lender)/date_work_month if date_work_month and (date_work_real - date_work_lender) > 0 else 0
                    columns_total += [
                        {'name': f"{Decimal(mm_month_total * 100).to_integral_value(rounding=ROUND_HALF_UP) / 100 if mm_month_total else ''}", 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    ]

                    date_work_project = 0
                    for line in resource_employee.filtered(lambda x: (x.order_id.project_id.en_department_id == department_id or x.order_id.project_id.en_project_type_id.is_presale) and x.order_id.project_id.stage_id.en_state in ['wait_for_execution', 'doing', 'complete'] and (x.date_start <= compared_from <= x.date_end or compared_from <= x.date_start <= compared_to)):
                        date_start_line = max(line.date_start, compared_from)
                        date_end_line = min(line.date_end, compared_to)
                        date_work_project += self.env['en.technical.model'].convert_daterange_to_count(employee, date_start_line, date_end_line) * line.workload
                    mm_month_project = date_work_project/date_work_month if date_work_month else 0

                    columns_project += [
                        {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                        {'name': f"{Decimal(mm_month_project * 100).to_integral_value(rounding=ROUND_HALF_UP) / 100 if mm_month_project else ''}", 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    ]
                    date_work_opp = 0
                    for line in resource_employee.filtered(lambda x: (x.order_id.project_id.en_department_id == department_id or x.order_id.project_id.en_project_type_id.is_presale) and x.order_id.project_id.stage_id.en_state in ['draft'] and (x.date_start <= compared_from <= x.date_end or compared_from <= x.date_start <= compared_to)):
                        date_start_line = max(line.date_start, compared_from)
                        date_end_line = min(line.date_end, compared_to)
                        date_work_opp += self.env['en.technical.model'].convert_daterange_to_count(employee, date_start_line, date_end_line) * line.workload
                    mm_month_opp = date_work_opp/date_work_month if date_work_month else 0

                    columns_opp += [
                        {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                        {'name': f"{Decimal(mm_month_opp * 100).to_integral_value(rounding=ROUND_HALF_UP) / 100 if mm_month_opp else ''}", 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    ]
                    mm_remain = mm_month_total - mm_month_project - mm_month_opp
                    if mm_remain < 0:
                        mm_remain = 0
                    columns_remain += [{'name': f"{Decimal(mm_remain * 100).to_integral_value(rounding=ROUND_HALF_UP) / 100 if round(mm_remain,2) else ''}", 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},]
                columns += columns_total + columns_project + columns_opp + columns_remain
                lines += [{
                    'id': f'department_{department_id.id}_employee_{employee.id}',
                    'name': employee.barcode or '',
                    'style': f'padding-left:8px;background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000',
                    'level': 1,
                    'columns': columns,
                    'unfoldable': True,
                    'unfolded': True,
                }]
                #level 2
                for project in resource_employee.filtered(
                        lambda x: (x.employee_id == employee and x.order_id.project_id.en_department_id == department_id)
                                  or (x.employee_id == employee and not x.order_id.project_id.en_department_id and x.employee_id.department_id == department_id)).mapped(
                    'order_id.project_id'):

                    if background == '#FFFFFF':
                        background = '#D8DAE0'
                    else:
                        background = '#FFFFFF'
                    columns_level_2 = [
                        {'name': '2', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                        {'name': employee.en_type_id.display_name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                        {'name': employee.name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                        {'name': employee.work_email or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                        {'name': employee.en_area_id.display_name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                        {'name': employee.en_block_id.display_name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                        {'name': employee.department_id.display_name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                        {'name': employee.en_department_id.display_name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                        {'name': employee.job_id.display_name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                        {'name': employee.en_level_id.display_name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                        {'name': employee.en_technique or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                        {'name': dict(employee.fields_get(['en_status'])['en_status']['selection'])[employee.en_status] if employee.en_status else '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                        {'name': employee.department_id.display_name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                        {'name': employee.en_date_start.strftime(lg.date_format) if employee.en_date_start else '', 'class': 'date', 'style': f'background-color:{background};text-align:left;vertical-align:middle; white-space:nowrap;border:1px solid #000000;'},
                        {'name': employee.departure_date.strftime(lg.date_format) if employee.departure_date else '', 'class': 'date', 'style': f'background-color:{background};text-align:left;vertical-align:middle; white-space:nowrap;border:1px solid #000000;'},
                    ]
                    columns_total_2 = []
                    columns_project_2 = []
                    columns_opp_2 = []
                    columns_remain_2 = []
                    for date_step in date_utils.date_range(datetime_from, datetime_to, relativedelta(months=1)):
                        compared_from = max(date_step + relativedelta(day=1), datetime_from).date()
                        compared_to = min(date_step + relativedelta(months=1, day=1, days=-1), datetime_to).date()
                        date_work_month = self.env['en.technical.model'].convert_daterange_to_count(employee, compared_from, compared_to, exclude_tech_type=['off', 'holiday'])
                        columns_total_2 += [
                            {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                        ]

                        date_work_project = 0
                        for line in resource_employee.filtered(lambda x: x.order_id.project_id == project and x.order_id.project_id.stage_id.en_state in ['wait_for_execution', 'doing', 'complete'] and (x.date_start <= compared_from <= x.date_end or compared_from <= x.date_start <= compared_to)):
                            date_start_line = max(line.date_start, compared_from)
                            date_end_line = min(line.date_end, compared_to)
                            date_work_project += self.env['en.technical.model'].convert_daterange_to_count(employee, date_start_line,date_end_line) * line.workload
                        mm_month_project = date_work_project / date_work_month if date_work_month else 0

                        columns_project_2 += [
                            {'name': f'{project.en_code if mm_month_project else ""}', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                            {'name': f"{Decimal(mm_month_project * 100).to_integral_value(rounding=ROUND_HALF_UP) / 100 if mm_month_project else ''}", 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                        ]
                        date_work_opp = 0
                        for line in resource_employee.filtered(
                                lambda x: x.order_id.project_id == project and x.order_id.project_id.stage_id.en_state in ['draft'] and (x.date_start <= compared_from <= x.date_end or compared_from <= x.date_start <= compared_to)):
                            date_start_line = max(line.date_start, compared_from)
                            date_end_line = min(line.date_end, compared_to)
                            date_work_opp += self.env['en.technical.model'].convert_daterange_to_count(employee, date_start_line, date_end_line) * line.workload
                        mm_month_opp = date_work_opp / date_work_month if date_work_month else 0

                        columns_opp_2 += [
                            {'name': f'{project.en_code if mm_month_opp else ""}', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                            {'name': f"{Decimal(mm_month_opp * 100).to_integral_value(rounding=ROUND_HALF_UP) / 100 if mm_month_opp else ''}", 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                        ]

                        columns_remain_2 += [
                            {'name': f"", 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                        ]
                    columns_level_2 += columns_total_2 + columns_project_2 + columns_opp_2 + columns_remain_2
                    lines += [{
                        'id': f'department_{department_id.id}_employee_{employee.id}_project_{project.id}',
                        'name': employee.barcode or '',
                        'style': f'padding-left:8px;background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000',
                        'level': 2,
                        'parent_id': f'department_{department_id.id}_employee_{employee.id}',
                        'columns': columns_level_2,
                    }]
                for department in department_id.employee_lender_report_ids.filtered(lambda x: x.employee_id == employee).mapped('borrow_department_id'):
                    for line in department_id.employee_lender_report_ids.filtered(lambda x: x.employee_id == employee and x.borrow_department_id == department and (x.date_start <= date_from <= x.date_end or date_from <= x.date_start <= date_to)):
                        if background == '#FFFFFF':
                            background = '#D8DAE0'
                        else:
                            background = '#FFFFFF'
                        columns_department = [
                            {'name': '1', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                            {'name': employee.en_type_id.display_name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                            {'name': employee.name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                            {'name': employee.work_email or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                            {'name': employee.en_area_id.display_name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                            {'name': employee.en_block_id.display_name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                            {'name': employee.department_id.display_name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                            {'name': employee.en_department_id.display_name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                            {'name': employee.job_id.display_name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                            {'name': employee.en_level_id.display_name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                            {'name': employee.en_technique or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                            {'name': dict(employee.fields_get(['en_status'])['en_status']['selection'])[employee.en_status] if employee.en_status else '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                            {'name': department.display_name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                            {'name': line.date_start.strftime(lg.date_format) if line.date_start else '', 'class': 'date', 'style': f'background-color:{background};text-align:left;vertical-align:middle; white-space:nowrap;border:1px solid #000000;'},
                            {'name': line.date_end.strftime(lg.date_format) if line.date_start else '', 'class': 'date', 'style': f'background-color:{background};text-align:left;vertical-align:middle; white-space:nowrap;border:1px solid #000000;'},
                        ]
                        columns_total = []
                        columns_project = []
                        columns_opp = []
                        columns_remain = []
                        for date_step in date_utils.date_range(datetime_from, datetime_to, relativedelta(months=1)):
                            compared_from = max(date_step + relativedelta(day=1), datetime_from).date()
                            compared_to = min(date_step + relativedelta(months=1, day=1, days=-1), datetime_to).date()
                            date_work_month = self.env['en.technical.model'].convert_daterange_to_count(employee, compared_from, compared_to,exclude_tech_type=['off', 'holiday'])
                            date_work_lender = 0
                            date_start_line = max(line.date_start, compared_from)
                            date_end_line = min(line.date_end, compared_to)
                            date_work_lender += self.env['en.technical.model'].convert_daterange_to_count(employee, date_start_line, date_end_line) * line.workload
                            mm_month_total = date_work_lender / date_work_month if date_work_month else 0
                            columns_total += [
                                {
                                    'name': f"{Decimal(mm_month_total * 100).to_integral_value(rounding=ROUND_HALF_UP) / 100 if mm_month_total else ''}",
                                    'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                            ]

                            date_work_project = 0
                            for resource in resource_employee.filtered(lambda x: x.order_id.project_id.en_department_id == department and x.order_id.project_id.stage_id.en_state in ['wait_for_execution', 'doing', 'complete'] and x.date_start >= line.date_start and x.date_end <= line.date_end):
                                date_start_line = max(resource.date_start, compared_from)
                                date_end_line = min(resource.date_end, compared_to)
                                date_work_project += self.env['en.technical.model'].convert_daterange_to_count(employee, date_start_line, date_end_line) * line.workload
                            mm_month_project = date_work_project / date_work_month if date_work_month else 0

                            columns_project += [
                                {'name': '',
                                 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                                {
                                    'name': f"{Decimal(mm_month_project * 100).to_integral_value(rounding=ROUND_HALF_UP) / 100 if mm_month_project else ''}",
                                    'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                            ]
                            date_work_opp = 0
                            for resource in resource_employee.filtered(lambda x: x.order_id.project_id.en_department_id == department and x.order_id.project_id.stage_id.en_state in ['draft'] and x.date_start >= line.date_start and x.date_end <= line.date_end):
                                date_start_line = max(resource.date_start, compared_from)
                                date_end_line = min(resource.date_end, compared_to)
                                date_work_opp += self.env['en.technical.model'].convert_daterange_to_count(employee, date_start_line, date_end_line) * line.workload
                            mm_month_opp = date_work_opp / date_work_month if date_work_month else 0

                            columns_opp += [
                                {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                                {'name': f"{Decimal(mm_month_opp * 100).to_integral_value(rounding=ROUND_HALF_UP) / 100 if mm_month_opp else ''}", 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                            ]
                            mm_remain = mm_month_total - mm_month_project - mm_month_opp
                            if mm_remain < 0:
                                mm_remain = 0
                            columns_remain += [
                                {'name': f"{Decimal(mm_remain * 100).to_integral_value(rounding=ROUND_HALF_UP) / 100 if round(mm_remain,2) else ''}", 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                            ]
                        columns_department += columns_total + columns_project + columns_opp + columns_remain
                        lines += [{
                            'id': f'lender_department_{department.id}_employee_{employee.id}',
                            'name': employee.barcode or '',
                            'style': f'padding-left:8px;background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000',
                            'level': 1,
                            'columns': columns_department,
                            'unfoldable': True,
                            'unfolded': True,
                        }]
                        #level 2
                        for project in resource_employee.filtered(lambda x: x.employee_id == employee and x.order_id.project_id.en_department_id == department and x.date_start >= line.date_start and x.date_end <= line.date_end).mapped('order_id.project_id'):
                            if background == '#FFFFFF':
                                background = '#D8DAE0'
                            else:
                                background = '#FFFFFF'
                            columns_department_level_2 = [
                                {'name': '2', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                                {'name': employee.en_type_id.display_name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                                {'name': employee.name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                                {'name': employee.work_email or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                                {'name': employee.en_area_id.display_name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                                {'name': employee.en_block_id.display_name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                                {'name': employee.department_id.display_name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                                {'name': employee.en_department_id.display_name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                                {'name': employee.job_id.display_name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                                {'name': employee.en_level_id.display_name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                                {'name': employee.en_technique or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                                {'name': dict(employee.fields_get(['en_status'])['en_status']['selection'])[employee.en_status] if employee.en_status else '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                                {'name': department.display_name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                                {'name': line.date_start.strftime(lg.date_format) if line.date_start else '', 'class': 'date', 'style': f'background-color:{background};text-align:left;vertical-align:middle; white-space:nowrap;border:1px solid #000000;'},
                                {'name': line.date_end.strftime(lg.date_format) if line.date_end else '', 'class': 'date', 'style': f'background-color:{background};text-align:left;vertical-align:middle; white-space:nowrap;border:1px solid #000000;'},
                            ]
                            columns_total_2 = []
                            columns_project_2 = []
                            columns_opp_2 = []
                            columns_remain_2 = []
                            for date_step in date_utils.date_range(datetime_from, datetime_to, relativedelta(months=1)):
                                compared_from = max(date_step + relativedelta(day=1), datetime_from).date()
                                compared_to = min(date_step + relativedelta(months=1, day=1, days=-1), datetime_to).date()
                                date_work_month = self.env['en.technical.model'].convert_daterange_to_count(employee, compared_from,compared_to, exclude_tech_type=['off', 'holiday'])
                                columns_total_2 += [
                                    {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                                ]

                                date_work_project = 0
                                for resource in resource_employee.filtered(lambda x: x.order_id.project_id.en_department_id == department and x.order_id.project_id == project and x.order_id.project_id.stage_id.en_state in ['wait_for_execution', 'doing', 'complete'] and (x.date_start <= compared_from <= x.date_end or compared_from <= x.date_start <= compared_to) and x.date_start >= line.date_start and x.date_end <= line.date_end):
                                    date_start_line = max(resource.date_start, compared_from)
                                    date_end_line = min(resource.date_end, compared_to)
                                    date_work_project += self.env['en.technical.model'].convert_daterange_to_count(employee, date_start_line, date_end_line) * line.workload
                                mm_month_project = date_work_project / date_work_month if date_work_month else 0

                                columns_project_2 += [
                                    {'name': f'{project.en_code if mm_month_project else ""}', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                                    {'name': f"{Decimal(mm_month_project * 100).to_integral_value(rounding=ROUND_HALF_UP) / 100 if mm_month_project else ''}", 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                                ]
                                date_work_opp = 0
                                for resource in resource_employee.filtered(lambda x: x.order_id.project_id.en_department_id == department and x.order_id.project_id == project and x.order_id.project_id.stage_id.en_state in ['draft'] and (x.date_start <= compared_from <= x.date_end or compared_from <= x.date_start <= compared_to) and x.date_start >= line.date_start and x.date_end <= line.date_end):
                                    date_start_line = max(resource.date_start, compared_from)
                                    date_end_line = min(resource.date_end, compared_to)
                                    date_work_opp += self.env['en.technical.model'].convert_daterange_to_count(employee, date_start_line, date_end_line) * line.workload
                                mm_month_opp = date_work_opp / date_work_month if date_work_month else 0

                                columns_opp_2 += [
                                    {'name': f'{project.en_code if mm_month_opp else ""}', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                                    {'name': f"{Decimal(mm_month_opp * 100).to_integral_value(rounding=ROUND_HALF_UP) / 100 if mm_month_opp else ''}", 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                                ]

                                columns_remain_2 += [
                                    {'name': f"", 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                                ]
                            columns_department_level_2 += columns_total_2 + columns_project_2 + columns_opp_2 + columns_remain_2
                            lines += [{
                                'id': f'lender_department_{department.id}_employee_{employee.id}_project_{project.id}',
                                'name': employee.barcode or '',
                                'style': f'padding-left:8px;background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000',
                                'level': 2,
                                'parent_id': f'lender_department_{department.id}_employee_{employee.id}',
                                'columns': columns_department_level_2,
                            }]

        return lines

