from odoo import models, fields, api, _
from datetime import timedelta, datetime, time
from odoo.tools import config, date_utils, get_lang, html2plaintext
from dateutil.relativedelta import relativedelta
from decimal import localcontext, Decimal, ROUND_HALF_UP


def daterange(start_date, end_date):
    for n in range(int(((end_date + timedelta(days=1)) - start_date).days)):
        yield start_date + timedelta(n)


class ResourceNonprojectAccountReportWizard(models.TransientModel):
    _name = "resource.nonproject.account.report.wizard"
    _description = "Thông tin nguồn lực ngoài dự án"

    unit = fields.Selection(string='Đơn vị', selection=[('MM', 'MM'), ('MD', 'MD'), ('MH', 'MH')],
                            default='MM', required=True)
    department_ids = fields.Many2many('hr.department', string='Trung tâm')
    is_hidden = fields.Boolean(string="Hiển thị nguồn lực ẩn", default=False)
    employee_ids = fields.Many2many('hr.employee', string='Tên nhân sự')
    resource_nonproject_planing_id = fields.Many2one("ngsc.nonproject.resource.planning")

    @api.onchange('department_ids')
    def _onchange_department_ids(self):
        result = {}
        for rec in self:
            rec.employee_ids = False
            if rec.department_ids:
                result['domain'] = {'employee_ids': [('department_id', 'in', rec.department_ids.ids)]}
            else:
                result['domain'] = {'employee_ids': [(1, '=', 1)]}
        return result

    def do(self):
        self = self.sudo()
        action = self.env.ref('account_reports.action_resource_account_report').read()[0]
        action['target'] = 'main'
        action['context'] = {'model': 'resource.nonproject.account.report',
                             'unit': self.unit,
                             'employee_ids': self.employee_ids.ids,
                             'department_ids': self.department_ids.ids,
                             'is_hidden': self.is_hidden,
                             'resource_nonproject_planing_id': self.resource_nonproject_planing_id.id}
        return action


def get_report_filename(options):
    """The name that will be used for the file when downloading pdf,xlsx,..."""
    date_start = fields.Date.from_string(options['date']['date_from'])
    date_end = fields.Date.from_string(options['date']['date_to'])
    if date_end and date_start:
        return f"Báo cáo Thông tin nguồn lực_{date_start.strftime('%d%m%Y')}_đến_{date_end.strftime('%d%m%Y')}"
    else:
        return 'Báo cáo Thông tin nguồn lực'


def _get_reports_buttons():
    return [
        {'name': _('XLSX'), 'sequence': 2, 'action': 'print_xlsx', 'file_export_type': _('XLSX')},
    ]


class ResourceNonprojectAccountReport(models.AbstractModel):
    _name = "resource.nonproject.account.report"
    _description = "Thông tin nguồn lực ngoài dự án"
    _inherit = "account.report"

    filter_date = {'mode': 'range', 'filter': 'this_month'}
    filter_all_entries = None
    filter_journals = None
    filter_analytic = None
    filter_unfold_all = False

    @api.model
    def _get_columns(self, options):
        unit = options.get('unit')
        columns_monthly = []
        columns_details = []
        date_from = min(fields.Date.from_string(options['date']['date_from']),
                        fields.Date.from_string(options['date']['date_to'])) + relativedelta(day=1)
        date_to = max(fields.Date.from_string(options['date']['date_from']),
                      fields.Date.from_string(options['date']['date_to'])) + relativedelta(day=1) + relativedelta(
            months=1) + relativedelta(days=-1)
        datetime_from = datetime.combine(date_from, time.min)
        datetime_to = datetime.combine(date_to, time.max)
        x = 0
        z = 14
        for date_step in date_utils.date_range(datetime_from, datetime_to, relativedelta(months=1)):
            x += 1
            columns_monthly += [{
                'pre-offset': z + 1,
                'name': f'{date_step.strftime("%m/%Y")}',
                'colspan': 4,
                'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'
            }]
            columns_details += [
                {'pre-offset': z + 1, 'name': 'Thời gian',
                 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
                {'pre-offset': z + 2, 'name': 'Mã dự án',
                 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
                {'pre-offset': z + 3, 'name': 'Workload',
                 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
                {'pre-offset': z + 4, 'name': f'{unit}',
                 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            ]
            z += 4
        for date_step in date_utils.date_range(datetime_from, datetime_to, relativedelta(months=1)):
            x += 1
            columns_monthly += [{
                'pre-offset': z + 1,
                'name': f'{date_step.strftime("%m/%Y")}',
                'colspan': 4,
                'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'
            }]
            columns_details += [
                {'pre-offset': z + 1, 'name': 'Thời gian',
                 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
                {'pre-offset': z + 2, 'name': 'Mã dự án',
                 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
                {'pre-offset': z + 3, 'name': 'Workload',
                 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
                {'pre-offset': z + 4, 'name': f'{unit}',
                 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            ]
            z += 4
        for date_step in date_utils.date_range(datetime_from, datetime_to, relativedelta(months=1)):
            x += 1
            columns_monthly += [{
                'pre-offset': z + 1,
                'name': f'{date_step.strftime("%m/%Y")}',
                'colspan': 4,
                'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'
            }]
            columns_details += [
                {'pre-offset': z + 1, 'name': 'Thời gian',
                 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
                {'pre-offset': z + 2, 'name': 'Mã Opp',
                 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
                {'pre-offset': z + 3, 'name': 'Workload',
                 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
                {'pre-offset': z + 4, 'name': f'{unit}',
                 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            ]
            z += 4
        for date_step in date_utils.date_range(datetime_from, datetime_to, relativedelta(months=1)):
            x += 1
            z += 1
            columns_monthly += [{
                'pre-offset': z,
                'rowspan': 2,
                'name': f'{date_step.strftime("%m/%Y")}',
                'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'
            }]
        columns_names = [
            {'name': 'Mã nhân sự', 'rowspan': 3,
             'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Level', 'rowspan': 3,
             'style': 'min-width:25px;background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap; border:1px solid #000000'},
            {'name': 'Loại', 'rowspan': 3,
             'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap; border:1px solid #000000'},
            {'name': 'Tên nhân sự', 'rowspan': 3,
             'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Email', 'rowspan': 3,
             'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Khu vực', 'rowspan': 3,
             'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Khối', 'rowspan': 3,
             'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Trung tâm', 'rowspan': 3,
             'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Phòng', 'rowspan': 3,
             'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Chức danh', 'rowspan': 3,
             'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Cấp bậc', 'rowspan': 3,
             'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Kỹ năng', 'rowspan': 3,
             'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Trạng thái', 'rowspan': 3,
             'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Ngày bắt đầu', 'rowspan': 3,
             'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Ngày kết thúc', 'rowspan': 3,
             'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Nguồn lực kế hoạch sử dụng trong dự án', 'colspan': int(x),
             'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Nguồn lực kế hoạch sử dụng ngoài dự án', 'colspan': int(x),
             'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Nguồn lực kế hoạch sử dụng trong Opp', 'colspan': int(x),
             'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Nguồn lực còn lại mà dự án có thể sử dụng', 'colspan': int(x),
             'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'}
        ]
        return [columns_names, columns_monthly, columns_details]

    @api.model
    def _get_report_name(self):
        ctx = self._context
        unit = ctx.get('unit')
        return f'''
                     Đơn vị       : {unit}<br/>
        '''

    def _set_context(self, options):
        ctx = super()._set_context(options)
        ctx['unit'] = ctx.get('unit')
        ctx['department_ids'] = ctx.get('department_ids')
        ctx['employee_ids'] = ctx.get('employee_ids')
        ctx['is_hidden'] = ctx.get('is_hidden')
        ctx['resource_nonproject_planing_id'] = ctx.get('resource_nonproject_planing_id')
        return ctx

    def _get_options(self, previous_options=None):
        res = super()._get_options(previous_options=previous_options)
        lst_key = ['unit', 'department_ids', 'employee_ids' ,'is_hidden' 'resource_nonproject_planing_id']
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
        maximum_workload = int(self.env['ir.config_parameter'].sudo().get_param('maximum_workload')) or 100
        lg = self.env['res.lang']._lang_get(self.env.user.lang) or get_lang(self.env)
        unit = options.get('unit')
        date_from = min(fields.Date.from_string(options['date']['date_from']),
                        fields.Date.from_string(options['date']['date_to'])) + relativedelta(day=1)
        date_to = max(fields.Date.from_string(options['date']['date_from']),
                      fields.Date.from_string(options['date']['date_to'])) + relativedelta(day=1) + relativedelta(
            months=1) + relativedelta(days=-1)
        datetime_from = datetime.combine(date_from, time.min)
        datetime_to = datetime.combine(date_to, time.max)
        department_ids = options.get('department_ids')
        employee_ids = options.get('employee_ids')
        is_hidden = options.get('is_hidden')
        net_working_day_months = self.env["en.technical.model"].sudo().count_net_working_days_by_months(date_from,
                                                                                                        date_to)
        resource_nonproject_planing_id = options.get('resource_nonproject_planing_id')
        domain_inactive = ['|', ('en_status', '!=', 'inactive'), '&', ('en_status', '=', 'inactive'),
                           ('departure_date', '>', date_from)]
        if resource_nonproject_planing_id:
            resource_nonproject = self.env["ngsc.nonproject.resource.planning"].sudo().browse(resource_nonproject_planing_id)
            employees = resource_nonproject.planning_line_ids.mapped("employee_id")
        else:
            domain = []
            if employee_ids:
                domain += [('id', 'in', employee_ids)]
            if not is_hidden:
                domain += [('is_hidden', '=', False)]
            if department_ids:
                domain += [('department_id', 'in', department_ids)]
                domain += domain_inactive
            employees = self.env['hr.employee'].sudo().with_context(active_test=False).search(domain)
            resource_nonproject = self.env["ngsc.nonproject.resource.planning"].sudo().search(
                [("date", ">=", date_from), ("date", "<=", date_to)])
        background = '#FFFFFF'
        leftover_tt = 0
        with localcontext() as ctx:
            ctx.rounding = ROUND_HALF_UP
            for employee in employees:
                nonproject_data = {}
                tech_data = self.env['en.technical.model'].convert_daterange_to_data(employee, datetime_from.date(),
                                                                                     datetime_to.date())
                detail_data = self.env['en.resource.detail'].convert_daterange_to_data(employee, datetime_from.date(),
                                                                                       datetime_to.date())
                if background == '#FFFFFF':
                    background = '#D8DAE0'
                else:
                    background = '#FFFFFF'
                columns = [
                    {'name': '1',
                     'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    {'name': employee.en_type_id.display_name or '',
                     'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    {'name': employee.name or '',
                     'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    {'name': employee.work_email or '',
                     'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    {'name': employee.en_area_id.display_name or '',
                     'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    {'name': employee.en_block_id.display_name or '',
                     'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    {'name': employee.department_id.display_name or '',
                     'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    {'name': employee.en_department_id.display_name or '',
                     'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    {'name': employee.job_id.display_name or '',
                     'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    {'name': employee.en_level_id.display_name or '',
                     'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    {'name': employee.en_technique or '',
                     'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    {'name': dict(employee.fields_get(['en_status'])['en_status']['selection'])[
                        employee.en_status] if employee.en_status else '',
                     'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    {'name': employee.en_date_start.strftime(lg.date_format) if employee.en_date_start else '',
                     'class': 'date',
                     'style': f'background-color:{background};text-align:left;vertical-align:middle; white-space:nowrap;border:1px solid #000000;'},
                    {'name': employee.departure_date.strftime(lg.date_format) if employee.departure_date else '',
                     'class': 'date',
                     'style': f'background-color:{background};text-align:left;vertical-align:middle; white-space:nowrap;border:1px solid #000000;'},
                ]
                calendar = employee.resource_calendar_id
                plus_columns = []
                nonproject_columns = []
                plus_child_columns = []
                extra_columns = []
                extra_child_columns = []
                child_columns = [
                    {'name': '2',
                     'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    {'name': employee.en_type_id.display_name or '',
                     'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    {'name': employee.name or '',
                     'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    {'name': employee.work_email or '',
                     'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    {'name': employee.en_area_id.display_name or '',
                     'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    {'name': employee.en_block_id.display_name or '',
                     'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    {'name': employee.department_id.display_name or '',
                     'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    {'name': employee.en_department_id.display_name or '',
                     'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    {'name': employee.job_id.display_name or '',
                     'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    {'name': employee.en_level_id.display_name or '',
                     'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    {'name': employee.en_technique or '',
                     'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    {'name': dict(employee.fields_get(['en_status'])['en_status']['selection'])[
                        employee.en_status] if employee.en_status else '',
                     'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    {'name': employee.en_date_start.strftime(lg.date_format) if employee.en_date_start else '',
                     'class': 'date',
                     'style': f'background-color:{background};text-align:left;vertical-align:middle; white-space:nowrap;border:1px solid #000000;'},
                    {'name': employee.departure_date.strftime(lg.date_format) if employee.departure_date else '',
                     'class': 'date',
                     'style': f'background-color:{background};text-align:left;vertical-align:middle; white-space:nowrap;border:1px solid #000000;'},
                ]
                project_child_columns = []
                opp_child_columns = []
                max_child_number = 0
                for date_step in date_utils.date_range(datetime_from, datetime_to, relativedelta(months=1)):
                    total_value = 0
                    plus_total_value = 0
                    compared_from = max(date_step + relativedelta(day=1), datetime_from).date()
                    compared_to = min(date_step + relativedelta(months=1, day=1, days=-1), datetime_to).date()
                    rslt = []
                    plus_rslt = []
                    dated = []
                    dmin = max(date_step + relativedelta(day=1), datetime_from).date()
                    dmax = min(date_step + relativedelta(months=1, day=1, days=-1), datetime_to).date()
                    hours_by_date = {}
                    leftover = 0  # giờ còn lại
                    total_left = 0  # giờ tổng
                    total_nonproject = 0
                    nonproject_planing = resource_nonproject.filtered(lambda x: x.date == compared_from).mapped("planning_line_ids")
                    nonproject = nonproject_planing.filtered(lambda x: x.employee_id == employee) if nonproject_planing else self.env["ngsc.nonproject.resource.planning.line"]
                    for d in daterange(dmin, dmax):
                        z = detail_data.get(d)
                        tech = tech_data.get(d)
                        if not tech:
                            continue
                        if tech.get('number') and z < 1:
                            dated += [d]
                            hours_by_date.setdefault(d, tech.get('number') - tech.get('number') * z)
                        if tech and tech.get('tech_type') not in ['off', 'holiday']:
                            total_left += calendar.hours_per_day
                        if tech and tech.get('tech_type') not in ['off', 'holiday', 'not_work', 'layoff']:
                            leftover += max(0, 1 - detail_data.get(d)) * 8
                    if maximum_workload > 100:
                        leftover += (maximum_workload - 100) * total_left / 100
                    if unit == 'MM':
                        if calendar.hours_per_day:
                            leftover = leftover / total_left if total_left else 0
                        else:
                            leftover = 0
                        leftover -= nonproject.total_nonproject_mm
                        total_nonproject = nonproject.total_nonproject_mm
                    if unit == 'MD':
                        if calendar.hours_per_day:
                            leftover = leftover / calendar.hours_per_day
                        else:
                            leftover = 0
                        leftover -= nonproject.total_nonproject_md
                        total_nonproject = nonproject.total_nonproject_md
                    if unit == 'MH':
                        leftover -= nonproject.total_nonproject_md * 8
                        total_nonproject = nonproject.total_nonproject_md * 8
                    state_resource = ['draft', 'to_approve', 'approved']
                    if self.env.context.get('print_mode'):
                        state_resource = ['approved']
                    for resource in self.env['en.resource.detail'].search([('order_id.active', '=', True), ('employee_id', '=', employee.id),('order_id.state', 'in', state_resource), '|','&', ('date_start', '<=', compared_from), ('date_end', '>=', compared_from),'&', ('date_start', '>=', compared_from), ('date_start', '<=', compared_to)],order='date_start asc'):
                        date_start = max(compared_from, resource.date_start)
                        date_end = min(compared_to, resource.date_end)
                        value = 0
                        mm_rate = net_working_day_months.get(str(compared_from), 22)
                        workload = resource.workload or 0
                        total_hours = self.env['en.technical.model'].convert_daterange_to_hours(employee, date_start,
                                                                                                date_end)
                        if mm_rate == 0 or workload == 0:
                            value = 0
                        else:
                            if unit == 'MM':
                                value += (total_hours * workload) / 8 / mm_rate
                            elif unit == 'MD':
                                value += (total_hours * workload) / 8
                            else:
                                value += total_hours
                        value = Decimal(value).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
                        if resource.order_id.project_id.en_state in ['doing', 'wait_for_execution', 'complete']:
                            if resource.order_id.state == 'approved':
                                total_value += value
                                rslt += [[
                                    f'<div style="white-space:nowrap;">{date_start.strftime(lg.date_format)} → {date_end.strftime(lg.date_format)}</div>',
                                    f'<div style="white-space:nowrap;">{resource.order_id.project_id.en_code}</div>',
                                    f'<div style="white-space:nowrap;">{Decimal(resource.workload * 1000).to_integral_value(rounding=ROUND_HALF_UP) / 10}%</div>',
                                    f'<div style="white-space:nowrap;text-align:right;">{value}</div>',
                                ]]
                            else:
                                rslt += [[
                                    f'<div style="white-space:nowrap;color:#0023F5">{date_start.strftime(lg.date_format)} → {date_end.strftime(lg.date_format)}</div>',
                                    f'<div style="white-space:nowrap;color:#0023F5">{resource.order_id.project_id.en_code}</div>',
                                    f'<div style="white-space:nowrap;color:#0023F5">{Decimal(resource.workload * 1000).to_integral_value(rounding=ROUND_HALF_UP) / 10}%</div>',
                                    f'<div style="white-space:nowrap;text-align:right;color:#0023F5">{value}</div>',
                                ]]
                        elif resource.order_id.project_id.en_state in ['draft']:
                            if resource.order_id.state == 'approved':
                                plus_total_value += value
                                plus_rslt += [[
                                    f'<div style="white-space:nowrap;">{date_start.strftime(lg.date_format)} → {date_end.strftime(lg.date_format)}</div>',
                                    f'<div style="white-space:nowrap;">{resource.order_id.project_id.en_code}</div>',
                                    f'<div style="white-space:nowrap;">{Decimal(resource.workload * 1000).to_integral_value(rounding=ROUND_HALF_UP) / 10}%</div>',
                                    f'<div style="white-space:nowrap;text-align:right;">{value}</div>',
                                ]]
                            else:
                                plus_rslt += [[
                                    f'<div style="white-space:nowrap;color:#0023F5">{date_start.strftime(lg.date_format)} → {date_end.strftime(lg.date_format)}</div>',
                                    f'<div style="white-space:nowrap;color:#0023F5">{resource.order_id.project_id.en_code}</div>',
                                    f'<div style="white-space:nowrap;color:#0023F5">{Decimal(resource.workload * 1000).to_integral_value(rounding=ROUND_HALF_UP) / 10}%</div>',
                                    f'<div style="white-space:nowrap;text-align:right;color:#0023F5">{value}</div>',
                                ]]
                    if leftover:
                        leftover_tt += leftover

                    leftover = Decimal(max([leftover * 1000, 0])).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
                    columns += [
                        {'name': '',
                         'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:nowrap;border:1px solid #000000'},
                        {'name': '',
                         'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:nowrap;border:1px solid #000000'},
                        {'name': '',
                         'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:nowrap;border:1px solid #000000'},
                        {
                            'name': f'{Decimal(total_value).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)}' if total_value else '',
                            'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:nowrap;border:1px solid #000000'},
                    ]
                    nonproject_columns += [
                        {'name': '',
                         'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:nowrap;border:1px solid #000000'},
                        {'name': '',
                         'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:nowrap;border:1px solid #000000'},
                        {'name': f'{Decimal(nonproject.total_nonproject_workload * 100).to_integral_value(rounding=ROUND_HALF_UP)}%',
                         'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:nowrap;border:1px solid #000000'},
                        {'name': f'{Decimal(total_nonproject).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)}',
                         'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:nowrap;border:1px solid #000000'},
                    ]
                    nonproject_data[str(fields.Date.from_string(date_step))] = nonproject.total_nonproject_workload
                    plus_columns += [
                        {'name': '',
                         'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:nowrap;border:1px solid #000000'},
                        {'name': '',
                         'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:nowrap;border:1px solid #000000'},
                        {'name': '',
                         'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:nowrap;border:1px solid #000000'},
                        {'name': f'{Decimal(plus_total_value).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)}' if plus_total_value else '',
                            'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:nowrap;border:1px solid #000000'},
                    ]
                    extra_columns += [{
                        'name': f'{Decimal(leftover / 1000).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)}' if leftover else '',
                        'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:nowrap;border:1px solid #000000'}]
                    project_child_columns += [rslt]
                    max_child_number = max(max_child_number, len(rslt))
                    opp_child_columns += [plus_rslt]
                    max_child_number = max(max_child_number, len(plus_rslt))
                    dated_txt = []
                    if dated:
                        dated.sort()
                        dated_txt = []
                        min_dated = dated[0]
                        max_dated = dated[0]
                        current_wl = 1.2 - detail_data.get(dated[0]) - nonproject.total_nonproject_workload
                        for d in dated:
                            wl = 1.2 - detail_data.get(d) - nonproject.total_nonproject_workload
                            if max_dated == d or current_wl == wl:
                                max_dated = d
                                current_wl = wl
                                continue
                            current_wl = Decimal(current_wl * 1000).to_integral_value(rounding=ROUND_HALF_UP)
                            if min_dated == max_dated:
                                dated_txt += [
                                    f'<div style="white-space:nowrap;">{max_dated.strftime(lg.date_format)} Workload: {current_wl / 10}%</div>'
                                ]
                                current_wl = wl
                            else:
                                dated_txt += [
                                    f'<div style="white-space:nowrap;">{min_dated.strftime(lg.date_format)} → {max_dated.strftime(lg.date_format)} Workload: {current_wl / 10}%</div>'
                                ]
                                current_wl = wl
                            min_dated = d
                            max_dated = d
                        else:
                            current_wl = Decimal(current_wl * 1000).to_integral_value(rounding=ROUND_HALF_UP)
                            if min_dated == max_dated:
                                dated_txt += [
                                    f'<div style="white-space:nowrap;">{max_dated.strftime(lg.date_format)} Workload: {current_wl / 10}%</div>'
                                ]
                            else:
                                dated_txt += [
                                    f'<div style="white-space:nowrap;">{min_dated.strftime(lg.date_format)} → {max_dated.strftime(lg.date_format)} Workload: {current_wl / 10}%</div>'
                                ]
                    extra_child_columns += [dated_txt]
                    max_child_number = max(max_child_number, len(dated_txt))
                is_child = True if max_child_number else False
                columns += nonproject_columns
                columns += plus_columns
                columns += extra_columns
                lines += [{
                    'id': 'employee_%s' % employee.id,
                    'name': employee.barcode or '',
                    'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000',
                    'level': 1,
                    'columns': columns,
                    'unfoldable': True if is_child else False,
                    'unfolded': self._need_to_unfold('employee_%s' % employee.id, options),
                }]
                if is_child:
                    for i in range(max_child_number):
                        new_child_columns = child_columns.copy()
                        for project in project_child_columns:
                            new_child_columns += [{'name': x,
                                                   'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'}
                                                  for x in (project[i] if len(project) > i else ['', '', '', ''])]
                            new_child_columns += [{'name': "",
                                                   'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'}
                                                  for x in (project[i] if len(project) > i else ['', '', '', ''])]
                        new_child_columns += [{'name': z,
                                               'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'}
                                              for opp in opp_child_columns for z in
                                              (opp[i] if len(opp) > i else ['', '', '', ''])]
                        new_child_columns += [{'name': d[i] if len(d) > i else '',
                                               'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'}
                                              for d in extra_child_columns]
                        child_columns += plus_child_columns
                        lines += [{
                            'id': 'detail_employee_%s' % employee.id,
                            'name': employee.barcode or '',
                            'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000',
                            'level': 2,
                            'columns': new_child_columns,
                            'parent_id': 'employee_%s' % employee.id,
                        }]
        return lines
