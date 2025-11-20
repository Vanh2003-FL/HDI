from odoo import models, fields, api, _
from odoo.tools.misc import format_date, DEFAULT_SERVER_DATE_FORMAT
from datetime import timedelta, datetime, time
from odoo.tools import config, date_utils, get_lang, html2plaintext
from dateutil.relativedelta import relativedelta
from decimal import localcontext, Decimal, ROUND_HALF_UP
from pytz import timezone
import math
from collections import defaultdict


class ResourceAnalysisReport(models.Model):
    _name = "resource.analysis.report"
    _description = "Báo cáo tổng hợp"

    employee_id = fields.Many2one('hr.employee', 'Nhân sự')
    en_type_id = fields.Many2one('en.type', related='employee_id.en_type_id')
    en_code = fields.Char(related='employee_id.barcode')
    en_mail = fields.Char(related='employee_id.work_email')
    en_area_id = fields.Many2one('en.name.area',related='employee_id.en_area_id')
    en_block_id = fields.Many2one('en.name.block', related='employee_id.en_block_id')
    department_id = fields.Many2one('hr.department', related='employee_id.department_id')
    en_department_id = fields.Many2one('en.department', related='employee_id.en_department_id')
    project_id = fields.Many2one('project.project', 'Dự án')
    date = fields.Date('Ngày')
    month_text = fields.Char(compute='_converts_date_month', string='Tháng')
    user_id = fields.Many2one('res.users')
    mm = fields.Float('MM')

    @api.depends('date')
    def _converts_date_month(self):
        for rec in self:
            if rec.date:
                rec.month_text = rec.date.strftime('%m/%Y')
            else:
                rec.month_text = ''

    def _get_missing_data(self):
        self = self.sudo()
        for rec in self:
            date_from, date_to = self._get_date_range()
            date_end_month = date_to + relativedelta(day=1, months=1, days=-1)

    def _get_date_range(self):
        date_from_txt = self._context.get('date_from') or fields.Date.Date.Date.context_today(self)
        date_to_txt = self._context.get('date_to') or fields.Date.Date.Date.context_today(self)
        date_from = min(fields.Date.from_string(date_from_txt), fields.Date.from_string(date_to_txt))
        date_to = max(fields.Date.from_string(date_from_txt), fields.Date.from_string(date_to_txt))
        return date_from, date_to

    def init_data(self):
        if self.env.user.has_group('ngsd_base.group_td'):
            self = self.sudo()
        date_from, date_to = self._get_date_range()
        today = fields.Date.Date.Date.context_today(self).strftime('%Y-%m-%d')
        datetime_from = datetime.combine(date_from, time.min)
        datetime_to = datetime.combine(date_to, time.max)
        self.env['resource.analysis.report'].sudo().search([]).unlink()
        domain = []
        resource_ids = self.env['en.resource.planning'].search([('state', '=', 'approved')])
        resource_details = self.env['en.resource.detail'].search([('order_id', 'in', resource_ids.ids), ('employee_id', '!=', False), '|',
                                                                          '&', ('date_start', '<=', date_from), ('date_end', '>=', date_from),
                                                                          '&', ('date_start', '>=', date_from), ('date_start', '<=', date_to), ])
        value = []
        for project in resource_details.mapped('order_id.project_id').sorted(lambda x: x.en_code.lower()):
            for employee in resource_details.filtered(lambda x: x.order_id.project_id == project).mapped('employee_id').sorted(lambda x: x.name.lower()):
                for date_step in date_utils.date_range(datetime_from, datetime_to, relativedelta(months=1)):
                    compared_from = max(date_step + relativedelta(day=1), datetime_from).date()
                    compared_to = min(date_step + relativedelta(months=1, day=1, days=-1), datetime_to).date()
                    value_create = {'date': compared_from, 'project_id': project.id, 'user_id': self.env.user.id, 'employee_id': employee.id}
                    resources = self.env['en.resource.detail'].search(
                        [('order_id.project_id', '=', project.id), ('order_id.state', '=', 'approved'),
                         ('employee_id', '=', employee.id), '|',
                         '&', ('date_start', '<=', compared_from), ('date_end', '>=', compared_from),
                         '&', ('date_start', '>=', compared_from), ('date_start', '<=', compared_to)],
                        order='date_start asc')
                    value_total_month = 0
                    for resource in resources:
                        date_start = max(compared_from, resource.date_start)
                        date_end = min(compared_to, resource.date_end)
                        workrange_hours = self.env['en.technical.model'].convert_daterange_to_hours(employee, date_start, date_end) * resource.workload
                        value_total_month += Decimal((workrange_hours / 8 / resource.order_id.mm_rate) * 100).to_integral_value(
                                rounding=ROUND_HALF_UP) if resource.order_id.mm_rate else 0
                    value_create['mm'] = value_total_month / 100
                    value.append(value_create)
        for i in value:
            self.env['resource.analysis.report'].create(i)
