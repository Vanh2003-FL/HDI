from odoo import models, fields, api, _, exceptions
from datetime import timedelta, datetime, time, date
from odoo.tools import config, date_utils, get_lang, html2plaintext
from dateutil.relativedelta import relativedelta
from decimal import localcontext, Decimal, ROUND_HALF_UP
from odoo.exceptions import UserError


class NGSBoundaryReportWizard(models.TransientModel):
    _name = "ngs.boundary.report.wizard"
    _description = "Báo cáo Định biên"

    en_fiscal_year_id = fields.Many2one('en.fiscal.year', string='Năm tài chính')
    date_from = fields.Date(string='Từ ngày')
    date_to = fields.Date(string='Đến ngày')
    time_options = fields.Selection([('en_fiscal_year', 'Năm tài chính'), ('option', 'Tùy chọn')], string='Thời gian', required=True)

    @api.onchange('date_from', 'date_to')
    def check_date(self):
        if self.date_to and self.date_from and self.date_to < self.date_from:
            raise UserError("'Đến ngày' phải lớn hơn hoặc bằng 'Từ ngày', vui lòng kiểm tra lại!")

    def do(self):
        self = self.sudo()
        action = self.env.ref('account_reports.action_boundary_report').read()[0]
        action['context'] = {
                'en_fiscal_year_id': self.en_fiscal_year_id.id,
                'date_from': self.date_from,
                'date_to': self.date_to,
                'time_options': self.time_options,
                'model': 'ngs.boundary.report',
            }

        return action


class NGSBoundaryReport(models.AbstractModel):
    _name = "ngs.boundary.report"
    _description = "Báo cáo Định biên"
    _inherit = "account.report"

    # filter_date = {'mode': 'range', 'filter': 'this_year'}
    filter_date = None
    filter_all_entries = None
    filter_journals = None
    filter_analytic = None
    filter_unfold_all = None

    def _get_options(self, previous_options=None):
        res = super()._get_options(previous_options=previous_options)
        lst_key = ['en_fiscal_year_id', 'date_from', 'date_to', 'time_options']
        for k in lst_key:
            if k in self._context:
                res[k] = self._context.get(k)
            else:
                res[k] = previous_options.get(k) if previous_options else False
        return res

    def _get_data_date(self, en_fiscal_year_id):
        en_fiscal_year = self.env['en.fiscal.year'].browse(en_fiscal_year_id)
        date_from = en_fiscal_year.start_date
        date_to = en_fiscal_year.end_date
        return date_from, date_to

    @api.model
    def _get_columns(self, options):
        columns_names = [
            {'name': ' ', 'style': 'padding-left:8px;background-color:#f2f2f2;text-align:center; white-space:nowrap; border:1px solid #000000;vertical-align: bottom;'},
            {'name': ' ', 'style': 'padding-left:8px;background-color:#f2f2f2;text-align:center; white-space:nowrap; border:1px solid #000000;vertical-align: bottom;'},
            {'name': 'Level', 'style': 'padding-left:8px;background-color:#f2f2f2;text-align:left; white-space:nowrap; border:1px solid #000000;vertical-align: bottom;'},
        ]
        if options.get('time_options') == 'en_fiscal_year':
            date_from, date_to = self._get_data_date(options.get('en_fiscal_year_id'))
            datetime_from = datetime.combine(date_from, time.min)
            datetime_to = datetime.combine(date_to, time.max)
        else:
            datetime_from = datetime.combine(datetime.strptime(options.get('date_from'),'%Y-%m-%d'), time.min)
            datetime_to = datetime.combine(datetime.strptime(options.get('date_to'), '%Y-%m-%d'), time.max)
        x = 0
        for date_step in date_utils.date_range(datetime_from, datetime_to, relativedelta(months=1)):
            x += 1
            columns_names += [{'pre-offset': 2 + x, 'name': f'T{date_step.month}.{date_step.year}', 'style': 'background-color:#d9e1f2;text-align:center; white-space:nowrap;vertical-align: bottom;'}]
        columns_names += [{'name': 'Định biên<br/>trung bình năm', 'style': 'background-color:#d9e1f2;text-align:center; white-space:nowrap;vertical-align: bottom;'}]
        return [columns_names]

    @api.model
    def _get_report_name(self):
        return 'Báo cáo Định biên'

    def _get_reports_buttons(self, options):
        return [
            {'name': _('XLSX'), 'sequence': 2, 'action': 'print_xlsx', 'file_export_type': _('XLSX')},
        ]

    @api.model
    def _get_lines(self, options, line_id=None):
        lines = []
        self = self.sudo()
        lg = self.env['res.lang']._lang_get(self.env.user.lang) or get_lang(self.env)
        if options.get('time_options') == 'en_fiscal_year':
            date_from, date_to = self._get_data_date(options.get('en_fiscal_year_id'))
            datetime_from = datetime.combine(date_from, time.min)
            datetime_to = datetime.combine(date_to, time.max)
        else:
            date_from = datetime.strptime(options.get('date_from'), '%Y-%m-%d')
            date_to = datetime.strptime(options.get('date_to'), '%Y-%m-%d')
            datetime_from = datetime.combine(date_from, time.min)
            datetime_to = datetime.combine(date_to, time.max)
        with localcontext() as options:
            options.rounding = ROUND_HALF_UP
            departments = self.env['hr.boundary.master'].search([('date', '!=', False), ('date', '>=', date_from),  ('date', '<=', date_to)]).department_id
            for idx, department in enumerate(departments, start=1):
                datas_group = self.env['hr.boundary.master'].read_group([('department_id', '=', department.id), ('date', '!=', False), ('date', '>=', date_from), ('date', '<=', date_to)],['date', 'hr_boundary'], ['date:month'])
                datas = {}
                for data in datas_group:
                    date_record = fields.Date.from_string(data.get('__range', {}).get('date', {}).get('from'))
                    datas[date_record] = data.get('hr_boundary')
                columns_total = [
                    {'name': department.block_id.name, 'style': f'font-weight:bold;background-color:#8ea9db;vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                    {'name': department.name, 'style': f'font-weight:bold;background-color:#8ea9db;vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                ]
                total = 0
                count = 0
                for date_step in date_utils.date_range(datetime_from, datetime_to, relativedelta(months=1)):
                    value = datas.get(date_step.date(), 0)
                    total += value
                    count += 1
                    columns_total += [{'name': str(value or ''), 'style': f'font-weight:bold;background-color:#8ea9db;vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'}]

                columns_total += [
                    {'name': str(round(total/count if count else 0)), 'style': f'font-weight:bold;background-color:#8ea9db;vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                ]
                lines += [{
                    'id': f'hr.department-{department.id}',
                    'name': str(idx),
                    'style': f'font-weight:bold;padding-left:8px;background-color:#8ea9db;vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000',
                    'level': 1,
                    'columns': columns_total,
                }]
                levels = self.env['hr.boundary.master'].search([('department_id', '=', department.id), ('date', '!=', False), ('date', '>=', date_from), ('date', '<=', date_to)]).en_name_level_id
                for level in levels:
                    datas_group_level = self.env['hr.boundary.master'].read_group([('department_id', '=', department.id), ('en_name_level_id', '=', level.id), ('date', '!=', False), ('date', '>=', date_from), ('date', '<=', date_to)], ['date', 'hr_boundary'], ['date:month'])
                    datas_level = {}
                    for data in datas_group_level:
                        date_record = fields.Date.from_string(data.get('__range', {}).get('date', {}).get('from'))
                        datas_level[date_record] = data.get('hr_boundary')
                    columns_total = [
                        {'name': department.name, 'style': f'background-color:#ffffff;vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                        {'name': level.name, 'style': f'background-color:#ffffff;vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    ]
                    total_level = 0
                    count_level = 0
                    for date_step in date_utils.date_range(datetime_from, datetime_to, relativedelta(months=1)):
                        value = datas_level.get(date_step.date(), 0)
                        total_level += value
                        count_level += 1
                        columns_total += [{'name': str(value or ''), 'style': f'background-color:#ffffff;vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'}]

                    columns_total += [
                        {'name': str(round(total_level/count_level if count_level else 0)), 'style': f'background-color:#ffffff;vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                    ]
                    lines += [{
                        'id': f'en.name.level-{level.id}',
                        'name': str(idx),
                        'style': f'padding-left:8px;background-color:#ffffff;vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000',
                        'level': 1,
                        'columns': columns_total,
                    }]

        return lines
