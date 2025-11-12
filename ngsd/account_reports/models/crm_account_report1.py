from odoo import models, fields, api, _
from odoo.tools.misc import format_date, DEFAULT_SERVER_DATE_FORMAT
from datetime import timedelta, datetime, time
from odoo.tools import config, date_utils, get_lang, html2plaintext
from dateutil.relativedelta import relativedelta
from decimal import localcontext, Decimal, ROUND_HALF_UP


class CrmAccountReport1(models.AbstractModel):
    _name = "crm.account.report1"
    _description = "Báo cáo tình trạng Lead"
    _inherit = "account.report"

    filter_date = {'mode': 'range', 'filter': 'this_month'}
    filter_all_entries = None
    filter_journals = None
    filter_analytic = None
    filter_unfold_all = None

    @api.model
    def _get_columns(self, options):
        columns_monthly = []

        date_from = min(fields.Date.from_string(options['date']['date_from']), fields.Date.from_string(options['date']['date_to']))
        date_to = max(fields.Date.from_string(options['date']['date_from']), fields.Date.from_string(options['date']['date_to']))

        records = self.env['crm.lead'].search([('company_id', 'in', self.env.companies.ids), ('date_deadline', '!=', False), ('date_deadline', '>=', date_from), ('date_deadline', '<=', date_to)])
        # records = self.env['crm.lead']
        # records |= self.env['x.crm.lead.invoice'].search([('lead_id.company_id', 'in', self.env.companies.ids), ('date', '!=', False), ('date', '>=', date_from), ('date', '<=', date_to)]).mapped('lead_id')
        # records |= self.env['x.crm.lead.payment'].search([('lead_id.company_id', 'in', self.env.companies.ids), ('date', '!=', False), ('date', '>=', date_from), ('date', '<=', date_to)]).mapped('lead_id')
        types = records.line_ids.mapped('type_id')
        invoice_colspan = 0
        dated_lst = records.x_lead_invoice.filtered_domain([('date', '!=', False)]).mapped('date')
        if dated_lst:
            date_from = datetime.combine(min(dated_lst), time.min)
            date_to = datetime.combine(max(dated_lst), time.max)

            for date_step in date_utils.date_range(date_from, date_to, relativedelta(months=1)):
                # columns_monthly.append({'pre-offset': 18 + len(columns_monthly) + len(types), 'name': f'Tháng {date_step.month}/{date_step.year} <br/>({max(date_step + relativedelta(day=1), date_from).strftime("%d/%m")} -> {min(date_step + relativedelta(months=1, day=1, days=-1), date_to).strftime("%d/%m")})', 'style': 'background-color:#798AAF;text-align:center; white-space:nowrap; border:1px solid #000000'})
                columns_monthly.append({'pre-offset': 18 + invoice_colspan + len(types), 'name': f'Tháng {date_step.month}/{date_step.year}', 'style': 'background-color:#798AAF;text-align:center; white-space:nowrap; border:1px solid #000000'})
                invoice_colspan += 1

        payment_colspan = 0
        dated_lst = records.x_lead_payment.filtered_domain([('date', '!=', False)]).mapped('date')
        if dated_lst:
            date_from = datetime.combine(min(dated_lst), time.min)
            date_to = datetime.combine(max(dated_lst), time.max)
            for date_step in date_utils.date_range(date_from, date_to, relativedelta(months=1)):
                # columns_monthly.append({'pre-offset': 19 + len(columns_monthly) + len(types), 'name': f'Tháng {date_step.month}/{date_step.year} <br/>({max(date_step + relativedelta(day=1), date_from).strftime("%d/%m")} -> {min(date_step + relativedelta(months=1, day=1, days=-1), date_to).strftime("%d/%m")})', 'style': 'background-color:#31869B;text-align:center; white-space:nowrap; border:1px solid #000000'})
                columns_monthly.append({'pre-offset': 19 + invoice_colspan + payment_colspan + len(types), 'name': f'Tháng {date_step.month}/{date_step.year}', 'style': 'background-color:#31869B;text-align:center; white-space:nowrap; border:1px solid #000000'})
                payment_colspan += 1
        columns_names = [
            {'name': 'Mã lead', 'rowspan': 2, 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;border:1px solid #000000'},
            {'name': 'Location', 'rowspan': 2, 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;border:1px solid #000000'},
            {'name': 'Đội kinh<br/>doanh', 'rowspan': 2, 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;border:1px solid #000000'},
            {'name': 'AM', 'rowspan': 2, 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;border:1px solid #000000'},
            {'name': 'Khách hàng', 'style': 'min-width:200px;background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;', 'rowspan': 2},
            {'name': 'Tên cơ hội/ dự án', 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;', 'rowspan': 2},
            {'name': 'Mô tả', 'style': 'min-width:350px;background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;', 'rowspan': 2},
            {'name': 'Trạng thái', 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;', 'rowspan': 2},
            {'name': '% KT', 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;', 'rowspan': 2},
            {'name': 'Đội Tư vấn', 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;', 'rowspan': 2},
            {'name': 'Đội sản<br/>xuất', 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;', 'rowspan': 2},
            {'name': 'Loại HĐ', 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;', 'rowspan': 2},
            {'name': 'Thời gian ký HĐ', 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;', 'rowspan': 2},
            {'name': 'Tổng giá trị dự án<br/>(Bao gồm cả VAT)', 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;', 'rowspan': 2},
            {'name': 'Giá trị HĐ', 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;', 'rowspan': 2}, ]

        for type in types.sorted('id'):
            columns_names += [
                {'name': type.name, 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;', 'rowspan': 2}
            ]
        columns_names += [
            {'name': 'TSLN<br/>(Dự kiến)', 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;', 'rowspan': 2},
            {'name': 'Lợi nhuận<br/>(Dự kiến)', 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;', 'rowspan': 2},
            {'name': 'Doanh thu xuất hoá đơn<br/>dự kiến', 'style': 'background-color:#798AAF;text-align:center; white-space:nowrap;', 'rowspan': 2},
            {'name': 'Xuất hóa đơn', 'style': 'background-color:#798AAF;text-align:center; white-space:nowrap;', 'colspan': invoice_colspan or 1},
            {'name': 'Tổng dòng tiền dự kiến', 'style': 'background-color:#31869B;text-align:center; white-space:nowrap;', 'rowspan': 2},
            {'name': 'Dòng tiền', 'style': 'background-color:#31869B;text-align:center; white-space:nowrap;', 'colspan': payment_colspan or 1},
        ]

        return [columns_names, columns_monthly]

    @api.model
    def _get_report_name(self):
        return self._description

    def _get_reports_buttons(self, options):
        return [
            # {'name': _('PDF'), 'sequence': 1, 'action': 'print_pdf', 'file_export_type': _('PDF')},
            {'name': _('XLSX'), 'sequence': 2, 'action': 'print_xlsx', 'file_export_type': _('XLSX')},
        ]

    @api.model
    def _get_lines(self, options, line_id=None):
        lines = []
        lg = self.env['res.lang']._lang_get(self.env.user.lang) or get_lang(self.env)
        date_from = min(fields.Date.from_string(options['date']['date_from']), fields.Date.from_string(options['date']['date_to']))
        date_to = max(fields.Date.from_string(options['date']['date_from']), fields.Date.from_string(options['date']['date_to']))

        records = self.env['crm.lead'].search([('company_id', 'in', self.env.companies.ids), ('date_deadline', '!=', False), ('date_deadline', '>=', date_from), ('date_deadline', '<=', date_to)])
        # records = self.env['crm.lead']
        # records |= self.env['x.crm.lead.invoice'].search([('lead_id.company_id', 'in', self.env.companies.ids), ('date', '!=', False), ('date', '>=', date_from), ('date', '<=', date_to)]).mapped('lead_id')
        # records |= self.env['x.crm.lead.payment'].search([('lead_id.company_id', 'in', self.env.companies.ids), ('date', '!=', False), ('date', '>=', date_from), ('date', '<=', date_to)]).mapped('lead_id')

        types = records.line_ids.mapped('type_id')

        invoice_datetime_from = False
        invoice_datetime_to = False

        dated_lst = records.x_lead_invoice.filtered_domain([('date', '!=', False)]).mapped('date')
        if dated_lst:
            invoice_datetime_from = datetime.combine(min(dated_lst), time.min)
            invoice_datetime_to = datetime.combine(max(dated_lst), time.max)

        payment_datetime_from = False
        payment_datetime_to = False
        dated_lst = records.x_lead_payment.filtered_domain([('date', '!=', False)]).mapped('date')
        if dated_lst:
            payment_datetime_from = datetime.combine(min(dated_lst), time.min)
            payment_datetime_to = datetime.combine(max(dated_lst), time.max)

        background = '#FFFFFF'
        with localcontext() as ctx:
            ctx.rounding = ROUND_HALF_UP
            for record in records:
                if background == '#FFFFFF':
                    background = '#D8DAE0'
                else:
                    background = '#FFFFFF'
                columns = [
                    {'name': record.partner_id.city or '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                    {'name': record.team_id.name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                    {'name': record.user_id.name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                    {'name': record.partner_id.name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                    {'name': record.name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:normal;border:1px solid #000000'},
                    {'name': record.description or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:normal;border:1px solid #000000'},
                    {'name': record.stage_id.name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                    {'name': f'{Decimal(record.probability).to_integral_value(rounding=ROUND_HALF_UP)}%', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                    {'name': ', '.join(record.mapped('x_consulting_team.name')), 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                    {'name': ', '.join(record.mapped('x_development_team.name')), 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                    {'name': record.x_project_type_id.name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                    {'name': record.date_deadline.strftime(lg.date_format) if record.date_deadline else '', 'class': 'date', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                    {'name': self.format_value(record.company_currency._convert(record.expected_revenue, self.env.company.currency_id, self.env.company, record.date_deadline or fields.Datetime.now()), self.env.company.currency_id, True), 'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:nowrap;border:1px solid #000000'},
                    {'name': self.format_value(record.company_currency._convert(record.ngsd_revenue, self.env.company.currency_id, self.env.company, record.date_deadline or fields.Datetime.now()), self.env.company.currency_id, True), f'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:nowrap;border:1px solid #000000'},
                ]
                for type in types.sorted('id'):
                    columns += [
                        {'name': self.format_value(sum(record.company_currency._convert(line.ngsd_revenue, self.env.company.currency_id, self.env.company, record.date_deadline or fields.Datetime.now()) for line in record.line_ids.filtered(lambda x: x.type_id == type)), self.env.company.currency_id, True), 'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:nowrap;border:1px solid #000000'}
                    ]

                columns += [
                    {'name': f'{Decimal(record.x_expected_ratio * 100).to_integral_value(rounding=ROUND_HALF_UP)}%', 'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:nowrap;border:1px solid #000000'},
                    {'name': self.format_value(record.company_currency._convert(record.x_expected_margin, self.env.company.currency_id, self.env.company, record.date_deadline or fields.Datetime.now()), self.env.company.currency_id, True), 'style': f'background-color:{background};vertical-align:middle;text-align:right; white-space:nowrap;border:1px solid #000000'},
                ]

                invoice_columns = []
                payment_columns = []
                invoice_total = payment_total = 0
                if invoice_datetime_from and invoice_datetime_to:
                    for date_step in date_utils.date_range(invoice_datetime_from, invoice_datetime_to, relativedelta(months=1)):
                        compared_from = (max(date_step + relativedelta(day=1), invoice_datetime_from)).date()
                        compared_to = (min(date_step + relativedelta(months=1, day=1, days=-1), invoice_datetime_to)).date()
                        invoice_value = sum(line.currency_id._convert(line.amount, self.env.company.currency_id, self.env.company, line.date) for line in record.x_lead_invoice.filtered(lambda x: x.date and compared_from <= x.date <= compared_to))
                        invoice_columns += [
                            {'name': self.format_value(invoice_value, self.env.company.currency_id, True), 'style': f'background-color:#D8DAE0;vertical-align:middle;text-align:right; white-space:nowrap;border:1px solid #000000'}
                        ]
                        invoice_total += invoice_value
                if payment_datetime_from and payment_datetime_to:
                    for date_step in date_utils.date_range(payment_datetime_from, payment_datetime_to, relativedelta(months=1)):
                        compared_from = (max(date_step + relativedelta(day=1), payment_datetime_from)).date()
                        compared_to = (min(date_step + relativedelta(months=1, day=1, days=-1), payment_datetime_to)).date()
                        payment_value = sum(line.currency_id._convert(line.amount, self.env.company.currency_id, self.env.company, line.date) for line in record.x_lead_payment.filtered(lambda x: x.date and compared_from <= x.date <= compared_to))
                        payment_columns += [
                            {'name': self.format_value(payment_value, self.env.company.currency_id, True), 'style': f'background-color:#D8DAE0;vertical-align:middle;text-align:right; white-space:nowrap;border:1px solid #000000'}
                        ]
                        payment_total += payment_value
                columns += [
                    {'name': self.format_value(invoice_total, self.env.company.currency_id, True), 'style': f'background-color:#798AAF;vertical-align:middle;text-align:right; white-space:nowrap;border:1px solid #000000'},
                ]
                columns += invoice_columns
                columns += [
                    {'name': self.format_value(payment_total, self.env.company.currency_id, True), 'style': f'background-color:#31869B;vertical-align:middle;text-align:right; white-space:nowrap;border:1px solid #000000'},
                ]
                columns += payment_columns

                lines += [{
                    'id': 'crm_lead_%s' % record.id,
                    'name': record.code or '',
                    'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000',
                    'level': 1,
                    'columns': columns,
                }]

            ngsd_revenue = sum(record.company_currency._convert(record.ngsd_revenue, self.env.company.currency_id, self.env.company, record.date_deadline or fields.Datetime.now()) for record in records)

            columns = [
                {'name': '', 'style': 'background-color:#717A91;vertical-align:middle;text-align:center; white-space:nowrap;border:0px solid #000000'},
                {'name': '', 'style': 'background-color:#717A91;vertical-align:middle;text-align:center; white-space:nowrap;border:0px solid #000000'},
                {'name': '', 'style': 'background-color:#717A91;vertical-align:middle;text-align:center; white-space:nowrap;border:0px solid #000000'},
                {'name': '', 'style': 'background-color:#717A91;vertical-align:middle;text-align:center; white-space:nowrap;border:0px solid #000000'},
                {'name': '', 'style': 'background-color:#717A91;vertical-align:middle;text-align:center; white-space:nowrap;border:0px solid #000000'},
                {'name': '', 'style': 'background-color:#717A91;vertical-align:middle;text-align:center; white-space:nowrap;border:0px solid #000000'},
                {'name': '', 'style': 'background-color:#717A91;vertical-align:middle;text-align:center; white-space:nowrap;border:0px solid #000000'},
                {'name': '', 'style': 'background-color:#717A91;vertical-align:middle;text-align:center; white-space:nowrap;border:0px solid #000000'},
                {'name': '', 'style': 'background-color:#717A91;vertical-align:middle;text-align:center; white-space:nowrap;border:0px solid #000000'},
                {'name': '', 'style': 'background-color:#717A91;vertical-align:middle;text-align:center; white-space:nowrap;border:0px solid #000000'},
                {'name': '', 'style': 'background-color:#717A91;vertical-align:middle;text-align:center; white-space:nowrap;border:0px solid #000000'},
                {'name': '', 'style': 'background-color:#717A91;vertical-align:middle;text-align:center; white-space:nowrap;border:0px solid #000000'},
                {'name': '', 'style': 'background-color:#717A91;vertical-align:middle;text-align:center; white-space:nowrap;border:0px solid #000000'},
                {'name': self.format_value(ngsd_revenue, self.env.company.currency_id, True), 'style': 'background-color:#717A91;vertical-align:middle;text-align:right; white-space:nowrap;border:0px solid #000000'},
            ]
            for type in types.sorted('id'):
                columns += [
                    {'name': '', 'style': 'background-color:#717A91;vertical-align:middle;text-align:right; white-space:nowrap;border:0px solid #000000'}
                ]

            columns += [
                {'name': '', 'style': 'background-color:#717A91;vertical-align:middle;text-align:right; white-space:nowrap;border:0px solid #000000'},
                {'name': '', 'style': 'background-color:#717A91;vertical-align:middle;text-align:right; white-space:nowrap;border:0px solid #000000'},
            ]

            invoice_columns = []
            payment_columns = []
            invoice_total = payment_total = 0
            if invoice_datetime_from and invoice_datetime_to:
                for date_step in date_utils.date_range(invoice_datetime_from, invoice_datetime_to, relativedelta(months=1)):
                    compared_from = (max(date_step + relativedelta(day=1), invoice_datetime_from)).date()
                    compared_to = (min(date_step + relativedelta(months=1, day=1, days=-1), invoice_datetime_to)).date()
                    invoice_value = sum(line.currency_id._convert(line.amount, self.env.company.currency_id, self.env.company, line.date) for line in records.mapped('x_lead_invoice').filtered(lambda x: x.date and compared_from <= x.date <= compared_to))
                    invoice_columns += [
                        {'name': self.format_value(invoice_value, self.env.company.currency_id, True), 'style': 'background-color:#798AAF;vertical-align:middle;text-align:right; white-space:nowrap;border:0px solid #000000'}
                    ]
                    invoice_total += invoice_value
            if payment_datetime_from and payment_datetime_to:
                for date_step in date_utils.date_range(payment_datetime_from, payment_datetime_to, relativedelta(months=1)):
                    compared_from = (max(date_step + relativedelta(day=1), payment_datetime_from)).date()
                    compared_to = (min(date_step + relativedelta(months=1, day=1, days=-1), payment_datetime_to)).date()
                    payment_value = sum(line.currency_id._convert(line.amount, self.env.company.currency_id, self.env.company, line.date) for line in records.mapped('x_lead_payment').filtered(lambda x: x.date and compared_from <= x.date <= compared_to))
                    payment_columns += [
                        {'name': self.format_value(payment_value, self.env.company.currency_id, True), 'style': 'background-color:#31869B;vertical-align:middle;text-align:right; white-space:nowrap;border:0px solid #000000'}
                    ]
                    payment_total += payment_value
            columns += [
                {'name': f'<span style="color:red">{self.format_value(invoice_total, self.env.company.currency_id, True)}</span>', 'style': 'background-color:#798AAF;vertical-align:middle;text-align:right; white-space:nowrap;border:0px solid #000000'},
            ]
            columns += invoice_columns
            columns += [
                {'name': f'<span style="color:red">{self.format_value(payment_total, self.env.company.currency_id, True)}</span>', 'style': 'background-color:#31869B;vertical-align:middle;text-align:right; white-space:nowrap;border:0px solid #000000'},
            ]
            columns += payment_columns

            lines += [{
                'id': 'total_crm_lead_%s' % self.env.user.id,
                'name': '',
                'class': 'total',
                'style': 'background-color:#717A91;vertical-align:middle;text-align:center; white-space:nowrap;border:0px solid #000000',
                'level': 1,
                'columns': columns,
            }]
        return lines
