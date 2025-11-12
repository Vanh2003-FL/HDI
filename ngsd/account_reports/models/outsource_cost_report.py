import pytz

from odoo import models, fields, api, _
from odoo.tools.misc import format_date, DEFAULT_SERVER_DATE_FORMAT
from datetime import timedelta, datetime, time
from odoo.tools import config, date_utils, get_lang, html2plaintext
from dateutil.relativedelta import relativedelta
from decimal import localcontext, Decimal, ROUND_HALF_UP
from pytz import timezone, UTC
import math
from collections import defaultdict


class OutsourceCostReportWizard(models.TransientModel):
    _name = "outsource.cost.report.wizard"
    _description = "Chi phí OS"

    employee_ids = fields.Many2many(comodel_name='hr.employee', string='Nhân viên', domain=[('en_type_id.is_os', '=', True)])
    period = fields.Selection(selection=[
        ('optional', 'Tùy chọn'),
        ('this_month', 'Tháng này'),
        ('this_quarter', 'Quý này'),
        ('this_year', 'Năm nay'),
        ('this_week', 'Tuần này'),
        ('previous_month', 'Tháng trước'),
        ('previous_quarter', 'Quý trước'),
        ('previous_year', 'Năm trước'),
        ('previous_week', 'Tuần trước'),
        ('next_week', 'Tuần sau'),
    ], string='Kỳ báo cáo', required=1, default='this_month')
    date_from = fields.Date('Từ', required=1)
    date_to = fields.Date('Đến', required=1)

    def button_confirm(self):
        self = self.sudo()
        action = self.env.ref('account_reports.outsource_cost_report_action').read()[0]
        action['target'] = 'main'
        action['context'] = {
            'model': 'outsource.cost.report',
            'employee_ids': self.employee_ids.ids,
            'date_from': self.date_from,
            'date_to': self.date_to,
        }
        return action

    @api.onchange('period')
    def onchange_period(self):
        today = fields.Date.today()
        period = self.period
        if period == 'this_month':
            start_date = today.replace(day=1)
            end_date = today + relativedelta(months=1, day=1, days=-1)
        elif period == 'this_quarter':
            start_date = (today - relativedelta(months=(today.month - 1) % 3)).replace(day=1)
            end_date = today
        elif period == 'this_year':
            start_date = today.replace(month=1, day=1)
            end_date = today + relativedelta(month=1, day=1, years=1, days=-1)
        elif period == 'this_week':
            start_date = today + relativedelta(weeks=-1, days=1, weekday=0)
            end_date = today + relativedelta(weekday=6)
        elif period == 'previous_month':
            start_date = (today + relativedelta(months=-1)).replace(day=1)
            end_date = today + relativedelta(days=-today.day)
        elif period == 'previous_quarter':
            start_date = (today - relativedelta(months=(today.month - 1) % 3) - relativedelta(months=3)).replace(day=1)
            end_date = today - relativedelta(months=(today.month - 1) % 3) - relativedelta(days=today.day)
        elif period == 'previous_year':
            start_date = (today + relativedelta(years=-1)).replace(day=1, month=1)
            end_date = (today + relativedelta(years=-1)).replace(day=31, month=12)
        elif period == 'previous_week':
            start_date = today + relativedelta(weeks=-2, days=1, weekday=0)
            end_date = today + relativedelta(weeks=-1, weekday=6)
        elif period == 'next_week':
            start_date = today + relativedelta(weeks=0, days=1, weekday=0)
            end_date = today + relativedelta(weeks=1, weekday=6)
        else:
            start_date = datetime.strptime(self._context.get('start_date') or today.strftime('%Y-%m-%d'), '%Y-%m-%d')
            end_date = datetime.strptime(self._context.get('end_date') or today.strftime('%Y-%m-%d'), '%Y-%m-%d')
        self.date_from = start_date
        self.date_to = end_date


class OutsourceCostReport(models.AbstractModel):
    _name = "outsource.cost.report"
    _description = "Chi phí OS"
    _inherit = "account.report"

    filter_date = None
    filter_all_entries = None
    filter_journals = None
    filter_analytic = None
    filter_unfold_all = None

    @api.model
    def _get_columns(self, options):
        columns_names = [
            {'name': '', 'style': 'min-width:25px;background-color:#dbe9f7;color:black;text-align:left; white-space:nowrap; border:1px solid #000000;'},
            {'name': 'Họ và Tên', 'style': 'min-width:25px;background-color:#dbe9f7;color:black;text-align:left; white-space:nowrap; border:1px solid #000000;'},
            {'name': 'Mã dự án', 'style': 'min-width:25px;background-color:#dbe9f7;color:black;text-align:left; white-space:nowrap; border:1px solid #000000;'},
            {'name': 'Dự án ', 'style': 'min-width:25px;background-color:#dbe9f7;color:black;text-align:left; white-space:nowrap; border:1px solid #000000;'},
            {'name': 'PM', 'style': 'min-width:25px;background-color:#dbe9f7;color:black;text-align:left; white-space:nowrap; border:1px solid #000000;'},
            {'name': 'Đơn vị (MD)', 'style': 'min-width:25px;background-color:#dbe9f7;color:black;text-align:left; white-space:nowrap; border:1px solid #000000;'},
            {'name': 'Tổng số giờ làm việc', 'style': 'min-width:25px;background-color:#dbe9f7;color:black;text-align:left; white-space:nowrap; border:1px solid #000000;'},
            {'name': 'Tổng số giờ làm thêm', 'style': 'min-width:25px;background-color:#dbe9f7;color:black;text-align:left; white-space:nowrap; border:1px solid #000000;'},
            {'name': 'Chi phí TS', 'style': 'min-width:25px;background-color:#dbe9f7;color:black;text-align:left; white-space:nowrap; border:1px solid #000000;'},
            {'name': 'Phí OT', 'style': 'min-width:25px;background-color:#dbe9f7;color:black;text-align:left; white-space:nowrap; border:1px solid #000000;'},
            {'name': 'Tổng  chi phí', 'style': 'min-width:25px;background-color:#dbe9f7;color:black;text-align:left; white-space:nowrap; border:1px solid #000000;'},
        ]

        date_from = fields.Date.from_string(options.get('date_from'))
        date_to = fields.Date.from_string(options.get('date_to'))
        datetime_from = datetime.combine(date_from, time.min)
        datetime_to = datetime.combine(date_to, time.max)
        for date_step in date_utils.date_range(datetime_from, datetime_to, relativedelta(days=1)):
            columns_names += [{'name': date_step.strftime('%d/%m'), 'style': 'min-width:25px;background-color:#dbe9f7;color:black;text-align:left; white-space:nowrap; border:1px solid #000000;'}]
        return [columns_names]

    @api.model
    def _get_report_name(self):
        date_start = fields.Date.from_string(self._context.get('date_from'))
        date_end = fields.Date.from_string(self._context.get('date_to'))
        if date_end and date_start:
            return f"Chi phí OS {date_start.strftime('%d%m%Y')}_{date_end.strftime('%d%m%Y')}"
        else:
            return 'Chi phí OS'

    def get_report_filename(self, options):
        """The name that will be used for the file when downloading pdf,xlsx,..."""
        date_start = fields.Date.from_string(options.get('date_from'))
        date_end = fields.Date.from_string(options.get('date_to'))
        if date_end and date_start:
            return f"Chi phí OS {date_start.strftime('%d%m%Y')}_{date_end.strftime('%d%m%Y')}"
        else:
            return 'Chi phí OS'

    def _get_reports_buttons(self, options):
        return [
            # {'name': _('PDF'), 'sequence': 1, 'action': 'print_pdf', 'file_export_type': _('PDF')},
            {'name': _('XLSX'), 'sequence': 2, 'action': 'print_xlsx', 'file_export_type': _('XLSX')},
        ]

    def _get_options(self, previous_options=None):
        res = super()._get_options(previous_options=previous_options)
        lst_key = ['employee_ids', 'date_from', 'date_to']
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
        # Convert ngày
        date_from = fields.Date.from_string(options['date_from'])
        date_to = fields.Date.from_string(options['date_to'])
        datetime_from = datetime.combine(date_from, time.min)
        datetime_to = datetime.combine(date_to, time.max)
        # Lấy các nhân viên thỏa mãn
        employee_ids = ctx.get('employee_ids', [])
        domain = [('en_type_id.is_os', '=', True)]
        if employee_ids:
            domain += [('id', 'in', employee_ids)]
        employee_ids = self.env['hr.employee'].search(domain).ids
        if not employee_ids:
            return lines
        # Nghỉ lễ
        date_holidays = []
        holidays = self.env['resource.calendar.leaves'].search([('is_holiday', '=', True)])
        for h in holidays:
            for t in date_utils.date_range(datetime.combine(h.date_from_convert, time.min), datetime.combine(h.date_to_convert, time.max), relativedelta(days=1)):
                date_holidays.append(t.date())

        self = self.with_context(no_format=True)
        background = '#FFFFFF'
        with localcontext() as ctx:
            ctx.rounding = ROUND_HALF_UP
            query_ts = f"""
                select emp.id employee_id, pp.id project_id, coalesce(min(e.id), 0) expense_id, l.date, sum(l.unit_amount) unit_amount, coalesce(min(expense), 0) expense, pp.name pp_name, pp.en_code pp_code, emp.name emp_name, min(p_pm.name) pm_name
                from account_analytic_line l
                join project_project pp on pp.id = l.project_id
                join hr_employee emp on emp.id = l.employee_id
                left join os_expense e on e.employee_id = l.employee_id and l.date between e.date_start and e.date_end
                left join res_users u_pm on u_pm.id = pp.user_id
                left join res_partner p_pm on p_pm.id = u_pm.partner_id
                where l.en_state = 'approved'
                and l.date between '{date_from}' and '{date_to}'
                and emp.id in {str(employee_ids).replace('[', '(').replace(']', ')')}
                group by emp.id, pp.id, l.date
            """
            self.env.cr.execute(query_ts)
            datas = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(dict))))
            for t in self.env.cr.dictfetchall():
                datas[t.get('employee_id')][t.get('project_id')][t.get('expense_id')]['expense'] = t.get('expense')
                datas[t.get('employee_id')][t.get('project_id')][t.get('expense_id')]['pp_name'] = t.get('pp_name')
                datas[t.get('employee_id')][t.get('project_id')][t.get('expense_id')]['pp_code'] = t.get('pp_code')
                datas[t.get('employee_id')][t.get('project_id')][t.get('expense_id')]['emp_name'] = t.get('emp_name')
                datas[t.get('employee_id')][t.get('project_id')][t.get('expense_id')]['pm_name'] = t.get('pm_name')
                datas[t.get('employee_id')][t.get('project_id')][t.get('expense_id')][t.get('date')]['ts'] = t.get('unit_amount')
            query_ot = f"""
                select emp.id employee_id, pp.id project_id, coalesce(min(e.id), 0) expense_id, ot.date, sum(ot.time) ot_time, coalesce(min(expense), 0) expense, pp.name pp_name, pp.en_code pp_code, emp.name emp_name, min(p_pm.name) pm_name
                from en_hr_overtime ot
                join project_project pp on pp.id = ot.project_id
                join hr_employee emp on emp.id = ot.employee_id
                left join os_expense e on e.employee_id = ot.employee_id and ot.date between e.date_start and e.date_end
                left join res_users u_pm on u_pm.id = pp.user_id
                left join res_partner p_pm on p_pm.id = u_pm.partner_id
                where ot.state = 'approved'
                and ot.date between '{date_from}' and '{date_to}'
                and emp.id in {str(employee_ids).replace('[', '(').replace(']', ')')}
                group by emp.id, pp.id, ot.date
            """
            self.env.cr.execute(query_ot)
            for t in self.env.cr.dictfetchall():
                datas[t.get('employee_id')][t.get('project_id')][t.get('expense_id')]['expense'] = t.get('expense')
                datas[t.get('employee_id')][t.get('project_id')][t.get('expense_id')]['pp_name'] = t.get('pp_name')
                datas[t.get('employee_id')][t.get('project_id')][t.get('expense_id')]['pp_code'] = t.get('pp_code')
                datas[t.get('employee_id')][t.get('project_id')][t.get('expense_id')]['emp_name'] = t.get('emp_name')
                datas[t.get('employee_id')][t.get('project_id')][t.get('expense_id')]['pm_name'] = t.get('pm_name')
                datas[t.get('employee_id')][t.get('project_id')][t.get('expense_id')][t.get('date')]['ot'] = t.get('ot_time')
            for employee_id in datas:
                for project_id in datas.get(employee_id):
                    for expense_id in datas.get(employee_id).get(project_id):
                        data = datas.get(employee_id).get(project_id).get(expense_id)
                        expense = data.get('expense') or 0
                        columns = [
                            {'name': data.get('emp_name') or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                            {'name': data.get('pp_code') or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                            {'name': data.get('pp_name') or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                            {'name': data.get('pm_name') or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                            {'name': expense, 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                        ]
                        ext_columns = []
                        total_ts = 0
                        total_ot = 0
                        cost_ts = 0
                        cost_ot = 0
                        for date_step in date_utils.date_range(datetime_from, datetime_to, relativedelta(days=1)):
                            ts = data.get(date_step.date(), {}).get('ts')
                            ot = data.get(date_step.date(), {}).get('ot')
                            name_list = []
                            if ts:
                                name_list.append('TS: %s'%ts)
                                total_ts += ts
                                cost_ts += ts * expense / 8
                            if ot:
                                name_list.append('OT: %s'%ot)
                                total_ot += ot
                                rate = 1.5
                                if date_step.weekday() in [5, 6]:
                                    rate = 2
                                if date_step.date in date_holidays:
                                    rate = 3
                                cost_ot += ot * rate * expense / 8
                            ext_columns.append({'name': '\n'.join(name_list), 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'})
                        columns += [
                            {'name': total_ts, 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                            {'name': total_ot, 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                            {'name': cost_ts, 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                            {'name': cost_ot, 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                            {'name': cost_ts + cost_ot, 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                        ]
                        columns += ext_columns
                        lines = [{
                            'id': 'emp%s-pp%s-expense%s' % (employee_id, project_id, expense_id),
                            'name': '',
                            'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000',
                            'level': 1,
                            'columns': columns,
                        }]

        return lines
