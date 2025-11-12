from odoo import models, fields, api, _
from odoo.tools.misc import format_date, DEFAULT_SERVER_DATE_FORMAT
from datetime import timedelta, datetime, time
from odoo.tools import config, date_utils, get_lang, html2plaintext
from dateutil.relativedelta import relativedelta
from decimal import localcontext, Decimal, ROUND_HALF_UP
from pytz import timezone
import math

class ProjectResourceAccountWizard(models.TransientModel):
    _name = "project.resource.account.wizard"
    _description = "Nguồn lực dự án"

    def _default_state_ids(self):
        return self.env['project.project.stage'].search([('en_state', 'not in', ['cancel'])]).ids

    project_ids = fields.Many2many('project.project', string='Dự án')
    state_ids = fields.Many2many('project.project.stage', string="Trạng thái", default=lambda self: self._default_state_ids())
    block_ids = fields.Many2many(comodel_name='en.name.block', string='Khối')
    department_ids = fields.Many2many(comodel_name='hr.department', string='Trung tâm', domain="[('block_id', 'in', block_ids)]")

    def do(self):
        self = self.sudo()
        action = self.env.ref('account_reports.action_project_resource_account_report').read()[0]
        action['target'] = 'main'
        action['context'] = {'model': 'project.resource.account.report',
                             'project_ids': self.project_ids.ids,
                             'state_ids': self.state_ids.ids,
                             'block_ids': self.block_ids.ids,
                             'department_ids': self.department_ids.ids,}
        return action


class ProjectResourceAccountReport(models.AbstractModel):
    _name = "project.resource.account.report"
    _description = "Nguồn lực dự án"
    _inherit = "account.report"

    filter_date = {'mode': 'range', 'filter': 'this_year'}
    filter_all_entries = None
    filter_journals = None
    filter_analytic = None
    filter_unfold_all = None

    @api.model
    def _get_columns(self, options):

        columns_names = [
            {'name': 'Cơ hội/Dự án', 'style': 'min-width:25px;background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap; border:1px solid #000000'},
            # {'name': 'Status', 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap; border:1px solid #000000'},
            {'name': 'Trạng thái dự án', 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Mã dự án', 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Trung tâm', 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Loại dự án', 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Các loại tiêu chí', 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Tổng', 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Lũy Kế tháng báo cáo', 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
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
            return f"Báo cáo Nguồn lực dự án_{date_start.strftime('%d%m%Y')}_đến_{date_end.strftime('%d%m%Y')}"
        else:
            return 'Báo cáo Nguồn lực dự án'

    def _get_reports_buttons(self, options):
        return [
            # {'name': _('PDF'), 'sequence': 1, 'action': 'print_pdf', 'file_export_type': _('PDF')},
            {'name': _('XLSX'), 'sequence': 2, 'action': 'print_xlsx', 'file_export_type': _('XLSX')},
        ]

    def _get_options(self, previous_options=None):
        res = super()._get_options(previous_options=previous_options)
        lst_key = ['project_ids', 'state_ids', 'block_ids', 'department_ids']
        for k in lst_key:
            if k in self._context:
                res[k] = self._context.get(k)
            else:
                res[k] = previous_options.get(k) if previous_options else False
            # v = previous_options and previous_options.get(k) or []
            # if self._context.get(k) or v:
            #     res[k] = self._context.get(k) or v
        return res

    @api.model
    def _get_lines(self, options, line_id=None):
        ctx = self._context
        lines = []
        lg = self.env['res.lang']._lang_get(self.env.user.lang) or get_lang(self.env)
        if self.env.user.has_group('ngsd_base.group_td'):
            self = self.sudo()
        date_from = min(fields.Date.from_string(options['date']['date_from']), fields.Date.from_string(options['date']['date_to'])) + relativedelta(day=1)
        date_to = max(fields.Date.from_string(options['date']['date_from']), fields.Date.from_string(options['date']['date_to'])) + relativedelta(day=1) + relativedelta(months=1) + relativedelta(days=-1)
        datetime_from = datetime.combine(date_from, time.min)
        datetime_to = datetime.combine(date_to, time.max)
        project_ids = options.get('project_ids')
        state_ids = options.get('state_ids')
        department_ids = options.get('department_ids')
        block_ids = options.get('block_ids')
        domain = []
        if project_ids or state_ids or block_ids or department_ids:
            if project_ids:
                domain += [('id', 'in', project_ids)]
            if state_ids:
                domain += [('stage_id', 'in', state_ids)]
            if block_ids:
                domain += [('en_block_id', 'in', block_ids)]
            if department_ids:
                domain += [('en_department_id', 'in', department_ids)]
            records = self.env['project.project'].search(domain + ['|',
                                                          '&', ('date_start', '<=', date_from), ('date', '>=', date_from),
                                                          '&', ('date_start', '>=', date_from), ('date_start', '<=', date_to), ])
        else:
            records = self.env['project.project'].search(['|',
                                                          '&', ('date_start', '<=', date_from), ('date', '>=', date_from),
                                                          '&', ('date_start', '>=', date_from), ('date_start', '<=', date_to), ])
        self = self.with_context(no_format=True)
        background = '#FFFFFF'
        with localcontext() as ctx:
            ctx.rounding = ROUND_HALF_UP
            for record in records:
                if background == '#FFFFFF':
                    background = '#D8DAE0'
                else:
                    background = '#FFFFFF'
                date_start_project = datetime.combine(record.date_start, time.min)
                total = sum(record.en_bmm_ids.mapped('bmm'))
                cummulative = sum(record.en_bmm_ids.filtered(lambda x: x.date and x.date <= date_to).mapped('bmm'))

                total = int(Decimal(total * 1000).to_integral_value(rounding=ROUND_HALF_UP)) / 1000
                cummulative = int(Decimal(cummulative * 1000).to_integral_value(rounding=ROUND_HALF_UP)) / 1000

                columns = []

                align = 'left'
                try:
                    if record.stage_id.display_name:
                        if float(record.stage_id.display_name):
                            align = 'right'
                except:
                    pass
                columns += [{'name': record.stage_id.display_name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:{align}; white-space:nowrap;border:1px solid #000000'}]

                align = 'left'
                try:
                    if record.en_code:
                        if float(record.en_code):
                            align = 'right'
                except:
                    pass
                columns += [{'name': record.en_code or '', 'style': f'background-color:{background};vertical-align:middle;text-align:{align}; white-space:nowrap;border:1px solid #000000'}]

                align = 'left'
                try:
                    if record.en_department_id.display_name:
                        if float(record.en_department_id.display_name):
                            align = 'right'
                except:
                    pass
                columns += [{'name': record.en_department_id.display_name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:{align}; white-space:nowrap;border:1px solid #000000'}]

                align = 'left'
                try:
                    if record.en_project_type_id.display_name:
                        if float(record.en_project_type_id.display_name):
                            align = 'right'
                except:
                    pass
                columns += [{'name': record.en_project_type_id.display_name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:{align}; white-space:nowrap;border:1px solid #000000'}]

                columns += [{'name': 'Budget', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'}]
                columns += [{'name': total if total else '', 'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:normal;border:1px solid #000000'}]
                columns += [{'name': cummulative if cummulative else '', 'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:normal;border:1px solid #000000'}]

                for date_step in date_utils.date_range(datetime_from, datetime_to, relativedelta(months=1)):
                    value = sum(record.en_bmm_ids.filtered(lambda x: x.month_txt == date_step.strftime('%m/%Y')).mapped('bmm'))
                    value = int(Decimal(value * 1000).to_integral_value(rounding=ROUND_HALF_UP)) / 1000

                    columns += [{'name': value if value else '', 'style': 'background-color:#3F4C6A;color:white;text-align:right; white-space:nowrap;'}]

                align = 'left'
                try:
                    if record.en_project_type_id.display_name:
                        if float(record.en_project_type_id.display_name):
                            align = 'right'
                except:
                    pass

                opp = 'Cơ hội' if record.stage_id.en_state == 'draft' else 'Dự án' if record.stage_id.en_state in ['wait_for_execution', 'doing'] else ''

                lines += [{
                    'id': 'project_bmm_%s' % record.id,
                    'name': opp,
                    'style': f'background-color:{background};vertical-align:middle;text-align:{align}; white-space:nowrap;border:1px solid #000000',
                    'level': 1,
                    'columns': columns,
                }]

                cummulative_plan = 0
                value = 0
                total_md = 0
                for line in record.en_resource_id.order_line:
                    for date_step in date_utils.date_range(date_start_project, datetime_to, relativedelta(months=1)):
                        compared_from = max(date_step + relativedelta(day=1), date_start_project).date()
                        compared_to = min(date_step + relativedelta(months=1, day=1, days=-1), datetime_to).date()
                        start_plan = line.date_start
                        end_plan = min(line.date_end, compared_to)
                        employee = line.employee_id

                        x = self.env['en.technical.model'].convert_daterange_to_hours(employee, max(start_plan, compared_from),
                                                                                      min(compared_to, end_plan))
                        value += x * line.workload

                cummulative_plan += value/8/record.mm_rate if record.mm_rate else 0
                cummulative_plan += sum(record.en_history_resource_ids.filtered(lambda x: (int(x.month) <= date_to.month and int(x.year) == date_to.year) or int(x.year) < date_to.year).mapped('plan'))
                for line in record.en_resource_id.order_line:
                    total_md += line.en_md
                total_md = total_md/record.mm_rate if record.mm_rate else 0
                history_plan_total = sum(record.en_history_resource_ids.mapped('plan'))
                # total_plan = int(Decimal((total_md + history_plan_total) * 1000).to_integral_value(rounding=ROUND_HALF_UP)) / 1000
                total_plan = int(Decimal((total_md + history_plan_total) * 1000).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)) / 1000
                cummulative_plan = int(Decimal(cummulative_plan * 1000).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)) / 1000
                columns = []
                align = 'left'
                try:
                    if record.stage_id.display_name:
                        if float(record.stage_id.display_name):
                            align = 'right'
                except:
                    pass
                columns += [{'name': record.stage_id.display_name or '',
                             'style': f'background-color:{background};vertical-align:middle;text-align:{align}; white-space:nowrap;border:1px solid #000000'}]

                align = 'left'
                try:
                    if record.en_code:
                        if float(record.en_code):
                            align = 'right'
                except:
                    pass
                columns += [{'name': record.en_code or '',
                             'style': f'background-color:{background};vertical-align:middle;text-align:{align}; white-space:nowrap;border:1px solid #000000'}]

                align = 'left'
                try:
                    if record.en_department_id.display_name:
                        if float(record.en_department_id.display_name):
                            align = 'right'
                except:
                    pass
                columns += [{'name': record.en_department_id.display_name or '',
                             'style': f'background-color:{background};vertical-align:middle;text-align:{align}; white-space:nowrap;border:1px solid #000000'}]

                align = 'left'
                try:
                    if record.en_project_type_id.display_name:
                        if float(record.en_project_type_id.display_name):
                            align = 'right'
                except:
                    pass
                columns += [{'name': record.en_project_type_id.display_name or '',
                             'style': f'background-color:{background};vertical-align:middle;text-align:{align}; white-space:nowrap;border:1px solid #000000'}]

                columns += [
                    {'name': 'Plan', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    {'name': total_plan if total_plan else '', 'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:normal;border:1px solid #000000'},
                    {'name': cummulative_plan if cummulative_plan else '', 'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:normal;border:1px solid #000000'},
                ]
                for date_step in date_utils.date_range(datetime_from, datetime_to, relativedelta(months=1)):
                    compared_from = max(date_step + relativedelta(day=1), datetime_from).date()
                    compared_to = min(date_step + relativedelta(months=1, day=1, days=-1), datetime_to).date()
                    value = 0
                    value_line = 0
                    for line in record.en_resource_id.order_line:
                        start_plan = line.date_start
                        end_plan = min(line.date_end, compared_to)
                        employee = line.employee_id

                        x = self.env['en.technical.model'].convert_daterange_to_hours(employee, max(start_plan, compared_from),
                                                                                      min(compared_to, end_plan))
                        value_line += x * line.workload
                    value += value_line/8/record.mm_rate if record.mm_rate else 0
                    value += sum(record.en_history_resource_ids.filtered(lambda x: (int(x.month) == compared_from.month and int(x.year) == compared_from.year)).mapped('plan'))
                    value = int(Decimal(value * 1000).to_integral_value(rounding=ROUND_HALF_UP)) / 1000
                    columns += [{'name': value if value else '', 'style': 'background-color:#3F4C6A;color:white;text-align:right; white-space:nowrap;'}]

                lines += [{
                    'id': 'project_plan_%s' % record.id,
                    'name': opp,
                    'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000',
                    'level': 1,
                    'columns': columns,
                }]
                total_ts = 0
                mm_rate = record.mm_rate
                for ts in self.env['account.analytic.line'].sudo().search([('project_id', '=', record.id)]):
                    if ts.en_state == 'approved':
                        total_ts += ts.unit_amount
                    if ts.ot_state == 'approved':
                        total_ts += ts.ot_time

                total_actual = (total_ts/8)/mm_rate if mm_rate else 0
                cummulative_actual = 0
                total_cummu_line = 0
                for line in self.env['account.analytic.line'].sudo().search([('project_id', '=', record.id), ('date', '>=', record.date_start), ('date', '<=', date_to)]):
                    if line.en_state == 'approved':
                        total_cummu_line += line.unit_amount
                    if line.ot_state == 'approved':
                        total_cummu_line += line.ot_time
                cummulative_actual += total_cummu_line/8/mm_rate if mm_rate else 0
                cummulative_actual += sum(record.en_history_resource_ids.filtered(lambda x: (int(x.month) <= date_to.month and int(x.year) == date_to.year) or int(x.year) < date_to.year).mapped('actual'))
                total_actual += sum(record.en_history_resource_ids.mapped('actual'))
                total_actual = int(Decimal(total_actual * 1000).to_integral_value(rounding=ROUND_HALF_UP)) / 1000
                cummulative_actual = int(Decimal(cummulative_actual * 1000).to_integral_value(rounding=ROUND_HALF_UP)) / 1000
                columns = []
                align = 'left'
                try:
                    if record.stage_id.display_name:
                        if float(record.stage_id.display_name):
                            align = 'right'
                except:
                    pass
                columns += [{'name': record.stage_id.display_name or '',
                             'style': f'background-color:{background};vertical-align:middle;text-align:{align}; white-space:nowrap;border:1px solid #000000'}]

                align = 'left'
                try:
                    if record.en_code:
                        if float(record.en_code):
                            align = 'right'
                except:
                    pass
                columns += [{'name': record.en_code or '',
                             'style': f'background-color:{background};vertical-align:middle;text-align:{align}; white-space:nowrap;border:1px solid #000000'}]

                align = 'left'
                try:
                    if record.en_department_id.display_name:
                        if float(record.en_department_id.display_name):
                            align = 'right'
                except:
                    pass
                columns += [{'name': record.en_department_id.display_name or '',
                             'style': f'background-color:{background};vertical-align:middle;text-align:{align}; white-space:nowrap;border:1px solid #000000'}]

                align = 'left'
                try:
                    if record.en_project_type_id.display_name:
                        if float(record.en_project_type_id.display_name):
                            align = 'right'
                except:
                    pass
                columns += [{'name': record.en_project_type_id.display_name or '',
                             'style': f'background-color:{background};vertical-align:middle;text-align:{align}; white-space:nowrap;border:1px solid #000000'}]
                columns += [
                    {'name': 'Actual', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    {'name': total_actual if total_actual else '', 'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:normal;border:1px solid #000000'},
                    {'name': cummulative_actual if cummulative_actual else '', 'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:normal;border:1px solid #000000'},
                ]
                for date_step in date_utils.date_range(datetime_from, datetime_to, relativedelta(months=1)):
                    compared_from = max(date_step + relativedelta(day=1), datetime_from).date()
                    compared_to = min(date_step + relativedelta(months=1, day=1, days=-1), datetime_to).date()
                    value = 0
                    value_line = 0

                    for line in self.env['account.analytic.line'].sudo().search([('project_id', '=', record.id), ('date', '>=', compared_from), ('date', '<=', compared_to)]):
                        if line.en_state == 'approved':
                            value_line += line.unit_amount
                        if line.ot_state == 'approved':
                            value_line += line.ot_time
                    value += value_line/8/mm_rate if mm_rate else 0
                    value += sum(record.en_history_resource_ids.filtered(lambda x: (int(x.month) == compared_from.month and int(x.year) == compared_from.year)).mapped('actual'))
                    value = int(Decimal(value * 1000).to_integral_value(rounding=ROUND_HALF_UP)) / 1000
                    columns += [{'name': value if value else '', 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;'}]

                lines += [{
                    'id': 'project_mmactual_%s' % record.id,
                    'name': opp,
                    'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000',
                    'level': 1,
                    'columns': columns,
                }]

        return lines

    @api.model
    def _get_lines_report_api(self, options):
        lines = []
        date_from = min(fields.Date.from_string(options['date']['date_from']), fields.Date.from_string(options['date']['date_to'])) + relativedelta(day=1)
        date_to = max(fields.Date.from_string(options['date']['date_from']), fields.Date.from_string(options['date']['date_to'])) + relativedelta(day=1) + relativedelta(months=1) + relativedelta(days=-1)
        datetime_from = datetime.combine(date_from, time.min)
        datetime_to = datetime.combine(date_to, time.max)
        records = self.env['project.project'].search(['|',
                                                      '&', ('date_start', '<=', date_from), ('date', '>=', date_from),
                                                      '&', ('date_start', '>=', date_from), ('date_start', '<=', date_to)])
        with localcontext() as ctx:
            ctx.rounding = ROUND_HALF_UP
            for record in records:
                opp = 'Opp' if record.stage_id.en_state == 'draft' else 'Project' if record.stage_id.en_state in ['wait_for_execution', 'doing'] else ''
                main_data = {
                    'Opp/Project': opp,
                    'Status': record.stage_id.display_name or '',
                    'Project_ID': record.en_code or '',
                    'Center': record.en_department_id.id,
                    'Project type': record.en_project_type_id.display_name or '',
                }

                # BMM
                total = sum(record.en_bmm_ids.mapped('bmm'))
                cummulative = sum(record.en_bmm_ids.filtered(lambda x: x.date and x.date <= date_to).mapped('bmm'))

                total = int(Decimal(total * 1000).to_integral_value(rounding=ROUND_HALF_UP)) / 1000
                cummulative = int(Decimal(cummulative * 1000).to_integral_value(rounding=ROUND_HALF_UP)) / 1000

                main_data_bmm = main_data.copy()
                main_data_bmm.update({
                    'Các loại tiêu chí': 'BMM',
                    'Tổng': total,
                    'Lũy Kế tháng báo cáo': cummulative,
                })
                for date_step in date_utils.date_range(datetime_from, datetime_to, relativedelta(months=1)):
                    value = sum(record.en_bmm_ids.filtered(lambda x: x.month_txt == date_step.strftime('%m/%Y')).mapped('bmm'))
                    value = int(Decimal(value * 1000).to_integral_value(rounding=ROUND_HALF_UP)) / 1000
                    row = main_data_bmm.copy()
                    row.update({
                        'Tháng': date_step.strftime('%m'),
                        'Năm': date_step.strftime('%Y'),
                        'Ngày': f'01/{date_step.strftime("%m/%Y")}',
                        'Giá trị': value,
                    })
                    lines.append(row)

                # PLAN
                cummulative = 0

                for line in record.en_resource_id.order_line:
                    if line.date_start > date_to:
                         continue
                    employee = line.employee_id

                    for date_step in date_utils.date_range(datetime_from, datetime_to, relativedelta(months=1)):
                        compared_from = (date_step + relativedelta(day=1)).date()
                        compared_to = (date_step + relativedelta(months=1, day=1, days=-1)).date()
                        date_end_resource_or_end = min(compared_to, line.date_end)
                        start_plan = line.date_start
                        x = self.env['en.technical.model'].convert_daterange_to_hours(employee, max(start_plan, compared_from), date_end_resource_or_end) / 8
                        cummulative += line.workload * x / record.mm_rate if record.mm_rate else 0
                cummulative += sum(record.en_history_resource_ids.filtered(lambda x: (int(x.month) <= date_to.month and int(x.year) == date_to.year) or int(x.year) < date_to.year).mapped('plan'))
                history_plan_total = sum(record.en_history_resource_ids.mapped('plan'))
                total = int(Decimal((record.en_resource_id.mm_conversion + history_plan_total) * 1000).to_integral_value(rounding=ROUND_HALF_UP)) / 1000
                cummulative = int(Decimal(cummulative * 1000).to_integral_value(rounding=ROUND_HALF_UP)) / 1000

                main_data_plan = main_data.copy()
                main_data_plan.update({
                    'Các loại tiêu chí': 'Plan',
                    'Tổng': total,
                    'Lũy Kế tháng báo cáo': cummulative,
                })
                for date_step in date_utils.date_range(datetime_from, datetime_to, relativedelta(months=1)):
                    compared_from = max(date_step + relativedelta(day=1), datetime_from).date()
                    compared_to = min(date_step + relativedelta(months=1, day=1, days=-1), datetime_to).date()
                    value = 0
                    value_line = 0
                    for line in record.en_resource_id.order_line:
                        employee = line.employee_id
                        start_plan = line.date_start
                        end_plan = min(line.date_end, compared_to)
                        x = self.env['en.technical.model'].convert_daterange_to_hours(employee, max(start_plan, compared_from),
                                                                                      min(compared_to, end_plan))
                        value_line += x * line.workload
                    value += value_line/8/record.mm_rate if record.mm_rate else 0
                    value = int(Decimal(value * 1000).to_integral_value(rounding=ROUND_HALF_UP)) / 1000

                    row = main_data_plan.copy()
                    row.update({
                        'Tháng': date_step.strftime('%m'),
                        'Năm': date_step.strftime('%Y'),
                        'Ngày': f'01/{date_step.strftime("%m/%Y")}',
                        'Giá trị': value,
                    })
                    lines.append(row)

                # MM actual
                total_ts = 0
                for ts in record.timesheet_ids:
                    if ts.en_state == 'approved':
                        total_ts += ts.unit_amount
                    if ts.ot_state == 'approved':
                        total_ts += ts.ot_time
                total = total_ts/8/record.mm_rate if record.mm_rate else 0
                cummulative = 0
                total_cummu_line = 0
                for line in record.mapped('timesheet_ids').filtered(lambda x: x.date and record.date_start <= x.date <= date_to):
                    if line.en_state == 'approved':
                        total_cummu_line += line.unit_amount
                    if line.ot_state == 'approved':
                        total_cummu_line += line.ot_time
                cummulative += total_cummu_line/8/record.mm_rate if record.mm_rate else 0
                cummulative += sum(record.en_history_resource_ids.filtered(lambda x: (int(x.month) <= date_to.month and int(x.year) == date_to.year) or int(x.year) < date_to.year).mapped('actual'))

                total = int(Decimal(total * 1000).to_integral_value(rounding=ROUND_HALF_UP)) / 1000
                cummulative = int(Decimal(cummulative * 1000).to_integral_value(rounding=ROUND_HALF_UP)) / 1000

                main_data_mm = main_data.copy()
                main_data_mm.update({
                    'Các loại tiêu chí': 'MM actual',
                    'Tổng': total,
                    'Lũy Kế tháng báo cáo': cummulative,
                })
                for date_step in date_utils.date_range(datetime_from, datetime_to, relativedelta(months=1)):
                    compared_from = max(date_step + relativedelta(day=1), datetime_from).date()
                    compared_to = min(date_step + relativedelta(months=1, day=1, days=-1), datetime_to).date()
                    value = 0
                    value_line = 0
                    for line in record.mapped('timesheet_ids').filtered(lambda x: x.date and compared_from <= x.date <= compared_to):
                        if line.en_state == 'approved':
                            value_line += line.unit_amount
                        if line.ot_state == 'approved':
                            value_line += line.ot_time
                    value += value_line / 8 / record.mm_rate if record.mm_rate else 0
                    value += sum(record.en_history_resource_ids.filtered(
                        lambda x: (int(x.month) == compared_from.month and int(x.year) == compared_from.year)).mapped('actual'))
                    value = int(Decimal(value * 1000).to_integral_value(rounding=ROUND_HALF_UP)) / 1000

                    row = main_data_mm.copy()
                    row.update({
                        'Tháng': date_step.strftime('%m'),
                        'Năm': date_step.strftime('%Y'),
                        'Ngày': f'01/{date_step.strftime("%m/%Y")}',
                        'Giá trị': value,
                    })
                    lines.append(row)

        return lines

    @api.model
    def _get_lines_report_slide_api(self, options):
        lines = []
        date_from = min(fields.Date.from_string(options['date']['date_from']), fields.Date.from_string(options['date']['date_to'])) + relativedelta(day=1)
        date_to = max(fields.Date.from_string(options['date']['date_from']), fields.Date.from_string(options['date']['date_to'])) + relativedelta(day=1) + relativedelta(months=1) + relativedelta(days=-1)
        datetime_from = datetime.combine(date_from, time.min)
        datetime_to = datetime.combine(date_to, time.max)
        records = self.env['hr.department'].search([])

        with localcontext() as ctx:
            ctx.rounding = ROUND_HALF_UP
            for record in records:
                department_id = record.id
                project_ids = self.env['project.project'].search([
                    ('en_department_id', '=', record.id),
                    '|', '&', ('date_start', '<=', date_from), ('date', '>=', date_from), '&', ('date_start', '>=', date_from),
                    ('date_start', '<=', date_to),
                ])
                resource_plans = self.env['en.resource.detail'].search(
                    [('order_id.project_id.en_department_id', '=', record.id), ('order_id.state', '=', 'approved')])

                timesheets = self.env['account.analytic.line'].search([
                    ('project_department_id', '=', record.id), ('en_state', '=', 'approved')
                ])

                for date_step in date_utils.date_range(datetime_from, datetime_to, relativedelta(months=1)):
                    compared_from = (date_step + relativedelta(day=1)).date()
                    compared_to = (date_step + relativedelta(months=1, day=1, days=-1)).date()
                    month_text = compared_from.strftime('%m')
                    year_text = compared_from.strftime('%Y')
                    line_data_project = []
                    line_data_project_opp = []

                    total_bmm_project = 0
                    total_bmm_opp = 0

                    value_plan_project = 0
                    value_plan_opp = 0

                    value_actual_project = 0
                    value_actual_opp = 0

                    for project in project_ids.filtered(lambda x: x.stage_id.en_state in ['wait_for_execution', 'doing', 'complete']):
                        value_bmm = sum(project.en_bmm_ids.filtered(lambda x: x.month_txt == date_step.strftime('%m/%Y')).mapped('bmm'))
                        total_bmm_project += value_bmm
                        value_plan_project += sum(project.en_history_resource_ids.filtered(
                            lambda x: int(x.month) == compared_from.month and int(x.year) == compared_from.year).mapped('plan'))
                        value_actual_project += sum(project.en_history_resource_ids.filtered(
                            lambda x: int(x.month) == compared_from.month and int(x.year) == compared_from.year).mapped('actual'))
                    for project in project_ids.filtered(lambda x: x.stage_id.en_state == 'draft'):
                        value_bmm = sum(project.en_bmm_ids.filtered(lambda x: x.month_txt == date_step.strftime('%m/%Y')).mapped('bmm'))
                        total_bmm_opp += value_bmm
                        value_plan_opp += sum(project.en_history_resource_ids.filtered(lambda x: int(x.month) == compared_from.month and int(x.year) == compared_from.year).mapped('plan'))
                        value_actual_opp += sum(project.en_history_resource_ids.filtered(lambda x: int(x.month) == compared_from.month and int(x.year) == compared_from.year).mapped('actual'))
                    for line in resource_plans.filtered(lambda x: x.order_id.project_id.stage_id.en_state in ['wait_for_execution', 'doing', 'complete']):
                        date_end_resource_or_end = min(compared_to, line.date_end)
                        employee = line.employee_id
                        y = line.order_id.project_id.mm_rate
                        x = self.env['en.technical.model'].convert_daterange_to_hours(employee, max(compared_from, line.date_start),
                                                                                      min(compared_to, date_end_resource_or_end)) * line.workload / 8
                        value_plan_project += x / y if y else 0
                    for line in resource_plans.filtered(lambda x: x.order_id.project_id.stage_id.en_state == 'draft'):
                        date_end_resource_or_end = min(compared_to, line.date_end)
                        employee = line.employee_id
                        y = line.order_id.project_id.mm_rate
                        x = self.env['en.technical.model'].convert_daterange_to_hours(employee, max(compared_from, line.date_start),
                                                                                      min(compared_to, date_end_resource_or_end)) * line.workload / 8
                        value_plan_opp += x / y if y else 0
                    for timesheet in timesheets.filtered(lambda x: x.project_id.stage_id.en_state in ['wait_for_execution', 'doing', 'complete'] and x.date and compared_from <= x.date <= compared_to):
                        value_ts_ot = timesheet.unit_amount
                        value_ts_ot += timesheet.ot_time if timesheet.ot_state == 'approved' else 0
                        value_actual_project += (value_ts_ot / 8)/timesheet.project_id.mm_rate if timesheet.project_id.mm_rate else 0
                    for timesheet in timesheets.filtered(lambda x: x.project_id.stage_id.en_state == 'draft' and x.date and compared_from <= x.date <= compared_to):
                        value_ts_ot = timesheet.unit_amount
                        value_ts_ot += timesheet.ot_time if timesheet.ot_state == 'approved' else 0
                        value_actual_opp += (value_ts_ot / 8)/timesheet.project_id.mm_rate if timesheet.project_id.mm_rate else 0
                    #BMM value
                    bmm_total = int(Decimal((total_bmm_project + total_bmm_opp) * 1000).to_integral_value(rounding=ROUND_HALF_UP)) / 1000
                    bmm_project = int(Decimal(total_bmm_project * 1000).to_integral_value(rounding=ROUND_HALF_UP)) / 1000
                    #Plan value
                    plan_total = int(Decimal((value_plan_project + value_plan_opp) * 1000).to_integral_value(rounding=ROUND_HALF_UP)) / 1000
                    plan_project = int(Decimal(value_plan_project * 1000).to_integral_value(rounding=ROUND_HALF_UP)) / 1000
                    #Actual value
                    actual_total = int(Decimal((value_actual_project + value_plan_opp) * 1000).to_integral_value(rounding=ROUND_HALF_UP)) / 1000
                    actual_project = int(Decimal(value_actual_project * 1000).to_integral_value(rounding=ROUND_HALF_UP)) / 1000

                    line_data_project_opp.append({
                        'Loại': 'Project+opp',
                        'Trung tâm': department_id,
                        'Chỉ số': 'BMM',
                        'Tháng': month_text,
                        'Năm': year_text,
                        'Ngày': f'01/{month_text}/{year_text}',
                        'Giá trị': bmm_total
                    })
                    line_data_project_opp.append({
                        'Loại': 'Project+opp',
                        'Trung tâm': department_id,
                        'Chỉ số': 'Plan',
                        'Tháng': month_text,
                        'Năm': year_text,
                        'Ngày': f'01/{month_text}/{year_text}',
                        'Giá trị': plan_total
                    })
                    line_data_project_opp.append({
                        'Loại': 'Project+opp',
                        'Trung tâm': department_id,
                        'Chỉ số': 'MM actual',
                        'Tháng': month_text,
                        'Năm': year_text,
                        'Ngày': f'01/{month_text}/{year_text}',
                        'Giá trị': actual_total
                    })
                    line_data_project.append({
                        'Loại': 'Project',
                        'Trung tâm': department_id,
                        'Chỉ số': 'BMM',
                        'Tháng': month_text,
                        'Năm': year_text,
                        'Ngày': f'01/{month_text}/{year_text}',
                        'Giá trị': bmm_project
                    })
                    line_data_project.append({
                        'Loại': 'Project',
                        'Trung tâm': department_id,
                        'Chỉ số': 'Plan',
                        'Tháng': month_text,
                        'Năm': year_text,
                        'Ngày': f'01/{month_text}/{year_text}',
                        'Giá trị': plan_project
                    })
                    line_data_project.append({
                        'Loại': 'Project',
                        'Trung tâm': department_id,
                        'Chỉ số': 'MM actual',
                        'Tháng': month_text,
                        'Năm': year_text,
                        'Ngày': f'01/{month_text}/{year_text}',
                        'Giá trị': actual_project
                    })
                    lines += line_data_project_opp
                    lines += line_data_project

                    # Manpower
                    value_manpower = 0
                    all_resources = project_ids.en_resource_id.order_line.filtered_domain([
                        '|',
                        '&', ('date_start', '<=', compared_from), ('date_end', '>=', compared_from),
                        '&', ('date_start', '>=', compared_from), ('date_start', '<=', compared_to)]
                    )
                    for line in all_resources:
                        employee = line.employee_id
                        if not employee.en_type_id.en_internal:
                            continue
                        value_manpower = self.env['en.technical.model'].convert_daterange_to_hours(employee, max(line.date_start, compared_from),
                                                                                      min(compared_to, line.date_end))
                    lines.append({
                        'Loại': '',
                        'Trung tâm': department_id,
                        'Chỉ số': 'Manpower',
                        'Tháng': month_text,
                        'Năm': year_text,
                        'Ngày': f'01/{month_text}/{year_text}',
                        'Giá trị': value_manpower
                    })
        return lines
