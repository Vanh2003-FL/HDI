from odoo import models, fields, api, _
from odoo.tools.misc import format_date, DEFAULT_SERVER_DATE_FORMAT
from datetime import timedelta, datetime, time
from odoo.tools import config, date_utils, get_lang, html2plaintext
from dateutil.relativedelta import relativedelta
from decimal import localcontext, Decimal, ROUND_HALF_UP
from pytz import timezone
import math


class PerformanceEvaluationWizard(models.TransientModel):
    _name = "performance.evaluation.wizard"
    _description = "Báo cáo đánh giá hiệu suất"

    department_ids = fields.Many2many('hr.department', string='Trung tâm', domain="[('block_id', 'in', block_ids)]")
    employee_ids = fields.Many2many('hr.employee', string='Nhân viên',
                                    domain="['|', ('department_id', 'in', department_ids), ('en_block_id', 'in', block_ids)]")
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
        action = self.env.ref('ngsc_performance_evaluation.action_performance_evaluation_report').read()[0]
        action['target'] = 'main'
        action['name'] = f'Báo cáo đánh giá hiệu suất Từ {self.date_from.strftime("%d/%m/%Y")} đến {self.date_to.strftime("%d/%m/%Y")}'
        action['display_name'] = f'Báo cáo đánh giá hiệu suất Từ {self.date_from.strftime("%d/%m/%Y")} đến {self.date_to.strftime("%d/%m/%Y")}'
        action['context'] = {'model': 'performance.evaluation.report',
                             'employee_ids': self.employee_ids.ids,
                             'department_ids': self.department_ids.ids,
                             'block_ids': self.block_ids.ids,
                             'date_from': self.date_from,
                             'date_to': self.date_to,
                             'id_popup': self.id,
                             'period': self.period,
                             }
        return action

class PerformanceEvaluationReport(models.AbstractModel):
    _name = "performance.evaluation.report"
    _description = "Báo cáo đánh giá hiệu suất"
    _inherit = "account.report"

    # filter_date = {'mode': 'range', 'filter': 'this_year'}
    filter_all_entries = None
    filter_journals = None
    filter_analytic = None
    filter_unfold_all = False

    @api.model
    def _get_report_name(self):
        return f'''Báo cáo đánh giá hiệu suất 
                '''

    def get_report_filename(self, options):
        """The name that will be used for the file when downloading pdf,xlsx,..."""
        date_start = fields.Date.from_string(options['date_from'])
        date_end = fields.Date.from_string(options['date_to'])
        if date_end and date_start:
            return f"Báo cáo đánh giá hiệu suất_{date_start.strftime('%d%m%Y')}_đến_{date_end.strftime('%d%m%Y')}"
        else:
            return 'Báo cáo đánh giá hiệu suất'

    def _get_reports_buttons(self, options):
        return [
            # {'name': _('PDF'), 'sequence': 1, 'action': 'print_pdf', 'file_export_type': _('PDF')},
            {'name': _('XLSX'), 'sequence': 2, 'action': 'print_xlsx', 'file_export_type': _('XLSX')},
            {'name': _('Chọn thông tin báo cáo'), 'sequence': 3, 'action': 'get_popup_report'},
        ]

    def get_popup_report(self, options):
        action = self.env['ir.actions.act_window']._for_xml_id('ngsc_performance_evaluation.performance_evaluation_wizard_act')
        action['res_id'] = options.get('id_popup')
        return action

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
    def _get_columns(self, options):
        columns_monthly = []
        columns_details = []

        columns_names = [
            {'name': 'STT', 'rowspan': 2,'style': 'padding-left:8px;background-color:#3F4C6A;color:white;text-align: center; white-space:nowrap; border:1px solid #000000'},
            # {'name': 'ID', 'rowspan': 2,'style': 'min-width:25px;background-color:#3F4C6A;color:white;text-align: center; white-space:nowrap; border:1px solid #000000'},
            {'name': 'Tháng', 'rowspan': 2,'style': 'background-color:#3F4C6A;color:white;text-align: center; white-space:nowrap; border:1px solid #000000'},
            {'name': 'ID nhân viên', 'rowspan': 2,'style': 'background-color:#3F4C6A;color:white;text-align: center; white-space:nowrap;'},
            {'name': 'Tên nhân viên', 'rowspan': 2,'style': 'background-color:#3F4C6A;color:white;text-align: center; white-space:nowrap;'},
            {'name': 'Khối', 'rowspan': 2,'style': 'background-color:#3F4C6A;color:white;text-align: center; white-space:nowrap;'},
            {'name': 'Trung tâm', 'rowspan': 2,'style': 'background-color:#3F4C6A;color:white;text-align: center; white-space:nowrap;'},
            {'name': 'Phòng', 'rowspan': 2,'style': 'background-color:#3F4C6A;color:white;text-align: center; white-space:nowrap;'},
            {'name': 'Effort', 'colspan': 5,'style': 'background-color:#3F4C6A;color:white;text-align: center; white-space:nowrap;'},
            {'name': 'Điểm thực tế', 'colspan': 3,'style': 'background-color:#3F4C6A;color:white;text-align: center; white-space:nowrap;'},
            {'name': 'Điểm quy đổi', 'colspan': 3,'style': 'background-color:#3F4C6A;color:white;text-align: center; white-space:nowrap;'},
            {'name': 'Điểm hiệu suất', 'rowspan': 2,'style': 'background-color:#3F4C6A;color:white;text-align: center; white-space:nowrap;'},
            {'name': 'Hạng đánh giá', 'rowspan': 2,'style': 'background-color:#3F4C6A;color:white;text-align: center; white-space:nowrap;'}
        ]

        z = 7
        columns_monthly = []
        for name in ['Effort dự kiến', 'Effort thực tế (Dự án)', 'Effort thực tế (Hỗ trợ dự án)', 'Effort thực tế (Ngoài dự án)', 'Effort thực tế (Tổng)'
                    , 'ĐTB Khối lượng công việc', 'ĐTB Chất lượng công việc', 'ĐTB Thái độ công việc'
                    , 'Đánh giá khối lượng', 'Đánh giá chất lượng', 'Đánh giá thái độ'
                    ]:
            columns_monthly += [{'pre-offset': z , 'name': name, 'rowspan': 1, 'style': 'background-color:#3F4C6A;color:white;text-align: center; white-space:nowrap;'}]
            z += 1

        return [columns_names, columns_monthly]

    @api.model
    def _get_lines(self, options, line_id=None):
        lines = []
        self = self.sudo()

        department_ids = options.get('department_ids')
        block_ids = options.get('block_ids')
        employee_ids = options.get('employee_ids')
        date_from = min(fields.Date.from_string(options['date_from']),
                        fields.Date.from_string(options['date_to'])) + relativedelta(day=1)
        date_to = max(fields.Date.from_string(options['date_from']),
                      fields.Date.from_string(options['date_to'])) + relativedelta(day=1) + relativedelta(
            months=1) + relativedelta(days=-1)

        background = '#FFFFFF'

        min_date_from = date_from
        max_date_to = date_to
        final_date_from = max([min_date_from, date_from]) + relativedelta(day=1)
        final_date_to = min([max_date_to, date_to]) + relativedelta(day=1) + relativedelta(months=1) + relativedelta(days=-1)
        datetime_from = datetime.combine(final_date_from, time.min)
        datetime_to = datetime.combine(final_date_to, time.max)

        month_display = [d.strftime("%m/%Y") for d in date_utils.date_range(datetime_from, datetime_to, relativedelta(months=1))]

        _ext_domain = []
        if department_ids:
            _ext_domain += [('department_id', 'in', department_ids)]
        if block_ids:
            _ext_domain += [('en_block_id', 'in', block_ids)]
        if employee_ids:
            _ext_domain += [('employee_id', 'in', employee_ids)]
        if month_display:
            _ext_domain += [('month_display', 'in', month_display)]
        records = self.env['ngsc.hr.performance.evaluation'].sudo().search(_ext_domain)

        with localcontext() as ctx:
            ctx.rounding = ROUND_HALF_UP
            stt_number = 1
            for department_id in records.mapped('employee_id.department_id').sorted(lambda x: x.name):
                for employee in records.filtered(lambda x: x.employee_id.department_id == department_id).mapped('employee_id').sorted(lambda x: x.barcode or ' '):
                    for project in records.filtered(lambda x: x.employee_id == employee):
                        columns = [
                            # {'name': stt_number, 'style': f'background-color:{background};vertical-align:middle;text-align: center; white-space:nowrap;border:1px solid #000000'},
                            # {'name': project.id or '', 'style': f'background-color:{background};vertical-align:middle;text-align: center; white-space:nowrap;border:1px solid #000000'},
                            {'name': project.month_display or '', 'style': f'background-color:{background};vertical-align:middle;text-align: center; white-space:nowrap;border:1px solid #000000'},
                            {'name': project.employee_id.barcode or '', 'style': f'background-color:{background};vertical-align:middle;text-align: center; white-space:nowrap;border:1px solid #000000'},
                            {'name': project.employee_id.name or '', 'style': f'background-color:{background};vertical-align:middle;text-align: center; white-space:nowrap;border:1px solid #000000'},
                            {'name': project.en_block_id.display_name or '', 'style': f'background-color:{background};vertical-align:middle;text-align: center; white-space:nowrap;border:1px solid #000000'},
                            {'name': project.department_id.display_name or '', 'style': f'background-color:{background};vertical-align:middle;text-align: center; white-space:nowrap;border:1px solid #000000'},
                            {'name': project.en_department_id.display_name or '', 'style': f'background-color:{background};vertical-align:middle;text-align: center; white-space:nowrap;border:1px solid #000000'},
                            {'name': project.hour_planned or '0', 'style': f'background-color:{background};vertical-align:middle;text-align: center; white-space:nowrap;border:1px solid #000000'},
                            {'name': project.hour_actual or '0', 'style': f'background-color:{background};vertical-align:middle;text-align: center; white-space:nowrap;border:1px solid #000000'},
                            {'name': project.hour_support_actual or '0', 'style': f'background-color:{background};vertical-align:middle;text-align: center; white-space:nowrap;border:1px solid #000000'},
                            {'name': project.hour_daily_waiting_task_actual or '0', 'style': f'background-color:{background};vertical-align:middle;text-align: center; white-space:nowrap;border:1px solid #000000'},
                            {'name': project.hour_actual or '0', 'style': f'background-color:{background};vertical-align:middle;text-align: center; white-space:nowrap;border:1px solid #000000'},
                            {'name': project.percentage_volume_evaluation or '0%', 'style': f'background-color:{background};vertical-align:middle;text-align: center; white-space:nowrap;border:1px solid #000000'},
                            {'name': project.quality_evaluation_real or '0', 'style': f'background-color:{background};vertical-align:middle;text-align: center; white-space:nowrap;border:1px solid #000000'},
                            {'name': project.attitude_evaluation or '0', 'style': f'background-color:{background};vertical-align:middle;text-align: center; white-space:nowrap;border:1px solid #000000'},
                            {'name': project.volume_evaluation or '0', 'style': f'background-color:{background};vertical-align:middle;text-align: center; white-space:nowrap;border:1px solid #000000'},
                            {'name': project.quality_evaluation or '0', 'style': f'background-color:{background};vertical-align:middle;text-align: center; white-space:nowrap;border:1px solid #000000'},
                            {'name': project.attitude_evaluation_dqd or '0', 'style': f'background-color:{background};vertical-align:middle;text-align: center; white-space:nowrap;border:1px solid #000000'},
                            {'name': project.performance_evaluation or '0', 'style': f'background-color:{background};vertical-align:middle;text-align: center; white-space:nowrap;border:1px solid #000000'},
                            {'name': project.rank_display or '', 'style': f'background-color:{background};vertical-align:middle;text-align: center; white-space:nowrap;border:1px solid #000000'},
                        ]

                        lines += [{
                            'id': f'month_display_{project.month_display}employee_{project.employee_id.id}',
                            'name': stt_number or '',
                            'style': f'padding-left:8px;background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000',
                            'level': 1,
                            'columns': columns,
                        }]
                        stt_number += 1
        return lines