from odoo import models, fields, api, _
from odoo.tools.misc import format_date, DEFAULT_SERVER_DATE_FORMAT
from datetime import timedelta, datetime, time
from odoo.tools import config, date_utils, get_lang, html2plaintext
from dateutil.relativedelta import relativedelta
from decimal import localcontext, Decimal, ROUND_HALF_UP
from pytz import timezone
import math

class DepartmentProjectReportWizard(models.TransientModel):
    _name = "department.project.report.wizard"
    _description = "Báo cáo dự án theo trung tâm"

    department_ids = fields.Many2many(comodel_name='hr.department', string='Trung tâm')

    def do(self):
        self = self.sudo()
        action = self.env.ref('account_reports.action_department_project_report_report').read()[0]
        action['target'] = 'main'
        action['context'] = {'model': 'department.project.report',
                             'department_ids': self.department_ids.ids,}
        return action


class DepartmentProjectReport(models.AbstractModel):
    _name = "department.project.report"
    _description = "Báo cáo dự án theo trung tâm"
    _inherit = "account.report"

    filter_date = {'mode': 'range', 'filter': 'this_year'}
    filter_all_entries = None
    filter_journals = None
    filter_analytic = None
    filter_unfold_all = None

    @api.model
    def _get_columns(self, options):

        columns_names = [
            {'name': 'Trung tâm', 'style': 'min-width:25px;background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap; border:1px solid #000000'},
            {'name': 'Loại', 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Tiêu chí', 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Tổng', 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            ]

        date_from = min(fields.Date.from_string(options['date']['date_from']), fields.Date.from_string(options['date']['date_to'])) + relativedelta(day=1)
        date_to = max(fields.Date.from_string(options['date']['date_from']), fields.Date.from_string(options['date']['date_to'])) + relativedelta(day=1) + relativedelta(months=1) + relativedelta(days=-1)
        datetime_from = datetime.combine(date_from, time.min)
        datetime_to = datetime.combine(date_to, time.max)
        for date_step in date_utils.date_range(datetime_from, datetime_to, relativedelta(months=1)):
            columns_names += [{'name': f'{date_step.strftime("%m/%Y")}', 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'}]

        return [columns_names]

    @api.model
    def _get_report_name(self):
        return self._description

    def get_report_filename(self, options):
        """The name that will be used for the file when downloading pdf,xlsx,..."""
        date_start = fields.Date.from_string(options['date']['date_from'])
        date_end = fields.Date.from_string(options['date']['date_to'])
        if date_end and date_start:
            return f"Báo cáo dự án theo trung tâm_{date_start.strftime('%d%m%Y')}_đến_{date_end.strftime('%d%m%Y')}"
        else:
            return 'Báo cáo dự án theo trung tâm'


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
        ctx = self._context
        lines = []
        lg = self.env['res.lang']._lang_get(self.env.user.lang) or get_lang(self.env)
        date_from = min(fields.Date.from_string(options['date']['date_from']), fields.Date.from_string(options['date']['date_to'])) + relativedelta(day=1)
        date_to = max(fields.Date.from_string(options['date']['date_from']), fields.Date.from_string(options['date']['date_to'])) + relativedelta(day=1) + relativedelta(months=1) + relativedelta(days=-1)
        datetime_from = datetime.combine(date_from, time.min)
        datetime_to = datetime.combine(date_to, time.max)
        department_ids = ctx.get('department_ids', [])
        domain = []
        if self.env.user.has_group('ngsd_base.group_td'):
            self = self.sudo()
        if department_ids:
            records = self.env['hr.department'].search([('id', 'in', department_ids)])
        else:
            records = self.env['hr.department'].search([])
        self = self.with_context(no_format=True)
        background = '#FFFFFF'
        with localcontext() as ctx:
            ctx.rounding = ROUND_HALF_UP
            for record in records:
                if background == '#FFFFFF':
                    background = '#D8DAE0'
                else:
                    background = '#FFFFFF'
                project_ids = self.env['project.project'].search([
                    ('en_department_id', '=', record.id),
                    '|', '&', ('date_start', '<=', date_from), ('date', '>=', date_from), '&', ('date_start', '>=', date_from), ('date_start', '<=', date_to),
                ])
                resource_plans = self.env['en.resource.detail'].search(
                    [('order_id.project_id.en_department_id', '=', record.id), ('order_id.state', '=', 'approved')])

                timesheets = self.env['account.analytic.line'].search([
                    ('project_department_id', '=', record.id), ('en_state', '=', 'approved')
                ])

                total_bmm_project = 0
                total_bmm_opp = 0
                total_plan_project = 0
                total_plan_opp = 0
                total_actual = 0
                total_actual_opp = 0

                columns_bmm = []
                columns_bmm_opp = []
                columns_bmm_total = []

                columns_plan = []
                columns_plan_opp = []
                columns_plan_total = []

                columns_actual = []
                columns_actual_opp = []
                columns_actual_total = []

                align = 'left'
                columns_bmm += [{'name': 'Dự án', 'style': f'background-color:{background};vertical-align:middle;text-align:{align}; white-space:nowrap;border:1px solid #000000'}]
                columns_bmm += [{'name': 'Bugget', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'}]
                columns_bmm_opp += [{'name': 'Cơ hội', 'style': f'background-color:{background};vertical-align:middle;text-align:{align}; white-space:nowrap;border:1px solid #000000'}]
                columns_bmm_opp += [{'name': 'Bugget', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'}]
                columns_bmm_total += [{'name': 'Dự án + Cơ hội', 'style': f'background-color:{background};vertical-align:middle;text-align:{align}; white-space:nowrap;border:1px solid #000000'}]
                columns_bmm_total += [{'name': 'Bugget', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'}]

                columns_plan += [{'name': 'Dự án', 'style': f'background-color:{background};vertical-align:middle;text-align:{align}; white-space:nowrap;border:1px solid #000000'}]
                columns_plan += [{'name': 'Plan', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'}]
                columns_plan_opp += [{'name': 'Cơ hội', 'style': f'background-color:{background};vertical-align:middle;text-align:{align}; white-space:nowrap;border:1px solid #000000'}]
                columns_plan_opp += [{'name': 'Plan', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'}]
                columns_plan_total += [{'name': 'Dự án + Cơ hội', 'style': f'background-color:{background};vertical-align:middle;text-align:{align}; white-space:nowrap;border:1px solid #000000'}]
                columns_plan_total += [{'name': 'Plan', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'}]

                columns_actual += [{'name': 'Dự án', 'style': f'background-color:{background};vertical-align:middle;text-align:{align}; white-space:nowrap;border:1px solid #000000'}]
                columns_actual += [{'name': 'Actual', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'}]
                columns_actual_opp += [{'name': 'Cơ hội', 'style': f'background-color:{background};vertical-align:middle;text-align:{align}; white-space:nowrap;border:1px solid #000000'}]
                columns_actual_opp += [{'name': 'Actual', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'}]
                columns_actual_total += [{'name': 'Dự án + Cơ hội', 'style': f'background-color:{background};vertical-align:middle;text-align:{align}; white-space:nowrap;border:1px solid #000000'}]
                columns_actual_total += [{'name': 'Actual', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'}]

                columns_bmm_month = []
                columns_bmm_month_opp = []
                columns_bmm_month_total = []
                columns_plan_month = []
                columns_plan_month_opp = []
                columns_plan_month_total = []
                columns_actual_month = []
                columns_actual_month_opp = []
                columns_actual_month_total = []
                for date_step in date_utils.date_range(datetime_from, datetime_to, relativedelta(months=1)):
                    compared_from = (date_step + relativedelta(day=1)).date()
                    compared_to = (date_step + relativedelta(months=1, day=1, days=-1)).date()
                    value_total = 0
                    value_total_opp = 0
                    value_plan_total = 0
                    value_plan_total_opp = 0
                    value_actual_total = 0
                    value_actual_total_opp = 0
                    for project in project_ids.filtered(lambda x: x.stage_id.en_state in ['wait_for_execution', 'doing', 'complete']):
                        value_bmm = sum(project.en_bmm_ids.filtered(lambda x: x.month_txt == date_step.strftime('%m/%Y')).mapped('bmm'))
                        total_bmm_project += value_bmm
                        value_total += int(Decimal(value_bmm * 1000).to_integral_value(rounding=ROUND_HALF_UP)) / 1000
                        value_plan_total += sum(project.en_history_resource_ids.filtered(lambda x: int(x.month) == compared_from.month and int(x.year) == compared_from.year).mapped('plan'))
                        value_actual_total += sum(project.en_history_resource_ids.filtered(lambda x: int(x.month) == compared_from.month and int(x.year) == compared_from.year).mapped('actual'))
                    for project in project_ids.filtered(lambda x: x.stage_id.en_state == 'draft'):
                        value_bmm = sum(project.en_bmm_ids.filtered(lambda x: x.month_txt == date_step.strftime('%m/%Y')).mapped('bmm'))
                        total_bmm_opp += value_bmm
                        value_total_opp += int(Decimal(value_bmm * 1000).to_integral_value(rounding=ROUND_HALF_UP)) / 1000
                        value_plan_total_opp += sum(project.en_history_resource_ids.filtered(lambda x: int(x.month) == compared_from.month and int(x.year) == compared_from.year).mapped('plan'))
                        value_actual_total_opp += sum(project.en_history_resource_ids.filtered(lambda x: int(x.month) == compared_from.month and int(x.year) == compared_from.year).mapped('actual'))
                    for line in resource_plans.filtered(lambda x: x.order_id.project_id.stage_id.en_state in ['wait_for_execution', 'doing', 'complete']):
                        date_end_resource_or_end = min(compared_to, line.date_end)
                        employee = line.employee_id
                        y = line.order_id.project_id.mm_rate
                        x = self.env['en.technical.model'].convert_daterange_to_hours(employee, max(compared_from, line.date_start),
                                                                                      min(compared_to, date_end_resource_or_end)) * line.workload / 8
                        value_plan_total += x / y if y else 0
                    for line in resource_plans.filtered(lambda x: x.order_id.project_id.stage_id.en_state == 'draft'):
                        date_end_resource_or_end = min(compared_to, line.date_end)
                        employee = line.employee_id
                        y = line.order_id.project_id.mm_rate
                        x = self.env['en.technical.model'].convert_daterange_to_hours(employee, max(compared_from, line.date_start),
                                                                                      min(compared_to, date_end_resource_or_end)) * line.workload / 8
                        value_plan_total_opp += x / y if y else 0
                    for timesheet in timesheets.filtered(lambda x: x.project_id.stage_id.en_state in ['wait_for_execution', 'doing', 'complete'] and x.date and compared_from <= x.date <= compared_to):
                        value_ts_ot = timesheet.unit_amount
                        value_ts_ot += timesheet.ot_time if timesheet.ot_state == 'approved' else 0
                        value_actual_total += (value_ts_ot / 8)/timesheet.project_id.mm_rate if timesheet.project_id.mm_rate else 0
                    for timesheet in timesheets.filtered(lambda x: x.project_id.stage_id.en_state == 'draft' and x.date and compared_from <= x.date <= compared_to):
                        value_ts_ot = timesheet.unit_amount
                        value_ts_ot += timesheet.ot_time if timesheet.ot_state == 'approved' else 0
                        value_actual_total_opp += (value_ts_ot / 8)/timesheet.project_id.mm_rate if timesheet.project_id.mm_rate else 0

                    total_actual += value_actual_total
                    total_actual_opp += value_actual_total_opp
                    total_plan_project += value_plan_total
                    total_plan_opp += value_plan_total_opp
                    value_plan_total = int(Decimal(value_plan_total * 1000).to_integral_value(rounding=ROUND_HALF_UP)) / 1000
                    value_plan_total_opp = int(Decimal(value_plan_total_opp * 1000).to_integral_value(rounding=ROUND_HALF_UP)) / 1000
                    value_actual_total = int(Decimal(value_actual_total * 1000).to_integral_value(rounding=ROUND_HALF_UP)) / 1000
                    value_actual_total_opp = int(Decimal(value_actual_total_opp * 1000).to_integral_value(rounding=ROUND_HALF_UP)) / 1000

                    value_bmm_total = int(Decimal((value_total + value_total_opp) * 1000).to_integral_value(rounding=ROUND_HALF_UP)) / 1000
                    value_plan = int(Decimal((value_plan_total + value_plan_total_opp) * 1000).to_integral_value(rounding=ROUND_HALF_UP)) / 1000
                    value_actual = int(Decimal((value_actual_total + value_actual_total_opp) * 1000).to_integral_value(rounding=ROUND_HALF_UP)) / 1000
                    columns_bmm_month += [{'name': Decimal(value_total * 1000).to_integral_value(rounding=ROUND_HALF_UP) / 1000 if value_total else '', 'style': 'background-color:#3F4C6A;color:white;text-align:right; white-space:nowrap;'}]
                    columns_bmm_month_opp += [{'name': int(Decimal(value_total_opp * 1000).to_integral_value(rounding=ROUND_HALF_UP)) / 1000 if value_total_opp else '', 'style': 'background-color:#3F4C6A;color:white;text-align:right; white-space:nowrap;'}]

                    columns_plan_month += [{'name': value_plan_total if value_plan_total else '', 'style': 'background-color:#3F4C6A;color:white;text-align:right; white-space:nowrap;'}]
                    columns_plan_month_opp += [{'name': value_plan_total_opp if value_plan_total_opp else '', 'style': 'background-color:#3F4C6A;color:white;text-align:right; white-space:nowrap;'}]

                    columns_bmm_month_total += [{'name': value_bmm_total if value_bmm_total else '', 'style': 'background-color:#3F4C6A;color:white;text-align:right; white-space:nowrap;'}]
                    columns_plan_month_total += [{'name': value_plan if value_plan else '', 'style': 'background-color:#3F4C6A;color:white;text-align:right; white-space:nowrap;'}]
                    columns_actual_month_total += [{'name': value_actual if value_actual else '', 'style': 'background-color:#3F4C6A;color:white;text-align:right; white-space:nowrap;'}]

                    columns_actual_month += [{'name': value_actual_total if value_actual_total else '',
                                            'style': 'background-color:#3F4C6A;color:white;text-align:right; white-space:nowrap;'}]
                    columns_actual_month_opp += [{'name': value_actual_total_opp if value_actual_total_opp else '',
                                                'style': 'background-color:#3F4C6A;color:white;text-align:right; white-space:nowrap;'}]
                #BMM
                total_bmm_project = int(Decimal(total_bmm_project * 1000).to_integral_value(rounding=ROUND_HALF_UP)) / 1000
                total_bmm_opp = int(Decimal(total_bmm_opp * 1000).to_integral_value(rounding=ROUND_HALF_UP)) / 1000
                total_bmm_total = int(Decimal((total_bmm_opp + total_bmm_project) * 1000).to_integral_value(rounding=ROUND_HALF_UP)) / 1000
                #PLAN
                total_plan_project = int(Decimal(total_plan_project * 1000).to_integral_value(rounding=ROUND_HALF_UP)) / 1000
                total_plan_opp = int(Decimal(total_plan_opp * 1000).to_integral_value(rounding=ROUND_HALF_UP)) / 1000
                total_plan_total = int(Decimal((total_plan_opp + total_plan_project) * 1000).to_integral_value(rounding=ROUND_HALF_UP)) / 1000
                #ACTUAL
                total_actual = int(Decimal(total_actual * 1000).to_integral_value(rounding=ROUND_HALF_UP)) / 1000
                total_actual_opp = int(Decimal(total_actual_opp * 1000).to_integral_value(rounding=ROUND_HALF_UP)) / 1000
                total_actual_total = int(Decimal((total_actual_opp + total_actual) * 1000).to_integral_value(rounding=ROUND_HALF_UP)) / 1000
                #BMM
                columns_bmm += [{'name': total_bmm_project if total_bmm_project else '',
                             'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:normal;border:1px solid #000000'}]
                columns_bmm += columns_bmm_month
                columns_bmm_opp += [{'name': total_bmm_opp if total_bmm_opp else '',
                             'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:normal;border:1px solid #000000'}]
                columns_bmm_opp += columns_bmm_month_opp
                #PLAN
                columns_plan += [{'name': total_plan_project if total_plan_project else '',
                             'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:normal;border:1px solid #000000'}]
                columns_plan += columns_plan_month
                columns_plan_opp += [{'name': total_plan_opp if total_plan_opp else '',
                                  'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:normal;border:1px solid #000000'}]
                columns_plan_opp += columns_plan_month_opp
                #ACTUAL
                columns_actual += [{'name': total_actual if total_actual else '',
                                  'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:normal;border:1px solid #000000'}]
                columns_actual += columns_actual_month
                columns_actual_opp += [{'name': total_actual_opp if total_actual_opp else '',
                                      'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:normal;border:1px solid #000000'}]
                columns_actual_opp += columns_actual_month_opp
                #total
                columns_bmm_total += [{'name': total_bmm_total if total_bmm_total else '',
                             'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:normal;border:1px solid #000000'}]
                columns_bmm_total += columns_bmm_month_total
                columns_actual_total += [{'name': total_actual_total if total_actual_total else '',
                             'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:normal;border:1px solid #000000'}]
                columns_actual_total += columns_actual_month_total
                columns_plan_total += [{'name': total_plan_total if total_plan_total else '',
                             'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:normal;border:1px solid #000000'}]
                columns_plan_total += columns_plan_month_total

                department_name = record.name if record.name else ''
                lines_bmm = [{
                    'id': 'project_bmm_%s' % record.id,
                    'name': department_name,
                    'style': f'background-color:{background};vertical-align:middle;text-align:{align}; white-space:nowrap;border:1px solid #000000',
                    'level': 1,
                    'columns': columns_bmm,
                }]
                lines_bmm_opp = [{
                    'id': 'project_bmm_opp_%s' % record.id,
                    'name': department_name,
                    'style': f'background-color:{background};vertical-align:middle;text-align:{align}; white-space:nowrap;border:1px solid #000000',
                    'level': 1,
                    'columns': columns_bmm_opp,
                }]
                lines_plan = [{
                    'id': 'project_plan_%s' % record.id,
                    'name': department_name,
                    'style': f'background-color:{background};vertical-align:middle;text-align:{align}; white-space:nowrap;border:1px solid #000000',
                    'level': 1,
                    'columns': columns_plan,
                }]
                lines_plan_opp = [{
                    'id': 'project_plan_opp_%s' % record.id,
                    'name': department_name,
                    'style': f'background-color:{background};vertical-align:middle;text-align:{align}; white-space:nowrap;border:1px solid #000000',
                    'level': 1,
                    'columns': columns_plan_opp,
                }]
                lines_actual = [{
                    'id': 'project_actual_%s' % record.id,
                    'name': department_name,
                    'style': f'background-color:{background};vertical-align:middle;text-align:{align}; white-space:nowrap;border:1px solid #000000',
                    'level': 1,
                    'columns': columns_actual,
                }]
                lines_actual_opp = [{
                    'id': 'project_actual_opp_%s' % record.id,
                    'name': department_name,
                    'style': f'background-color:{background};vertical-align:middle;text-align:{align}; white-space:nowrap;border:1px solid #000000',
                    'level': 1,
                    'columns': columns_actual_opp,
                }]
                lines_plan_total = [{
                    'id': 'project_plan_opp_%s' % record.id,
                    'name': department_name,
                    'style': f'background-color:{background};vertical-align:middle;text-align:{align}; white-space:nowrap;border:1px solid #000000',
                    'level': 1,
                    'columns': columns_plan_total,
                }]
                lines_actual_total = [{
                    'id': 'project_actual_%s' % record.id,
                    'name': department_name,
                    'style': f'background-color:{background};vertical-align:middle;text-align:{align}; white-space:nowrap;border:1px solid #000000',
                    'level': 1,
                    'columns': columns_actual_total,
                }]
                lines_bmm_total = [{
                    'id': 'project_actual_opp_%s' % record.id,
                    'name': department_name,
                    'style': f'background-color:{background};vertical-align:middle;text-align:{align}; white-space:nowrap;border:1px solid #000000',
                    'level': 1,
                    'columns': columns_bmm_total,
                }]
                lines += lines_bmm + lines_plan + lines_actual + lines_bmm_opp + lines_plan_opp + lines_actual_opp + lines_bmm_total + lines_plan_total + lines_actual_total


        return lines
