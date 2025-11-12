from odoo import models, fields, api, _
from odoo.tools.misc import format_date, DEFAULT_SERVER_DATE_FORMAT
from datetime import timedelta, datetime, time
from odoo.tools import config, date_utils, get_lang, html2plaintext
from dateutil.relativedelta import relativedelta
from decimal import localcontext, Decimal, ROUND_HALF_UP


class ContractAccountReport(models.AbstractModel):
    _name = "contract.account.report"
    _description = "Báo cáo hợp đồng"
    _inherit = "account.report"

    # filter_date = {'mode': 'range', 'filter': 'this_month'}
    filter_date = None
    filter_all_entries = None
    filter_journals = None
    filter_analytic = None
    filter_unfold_all = True

    @api.model
    def _get_columns(self, options):
        columns_names = [
            {'name': '', 'style': 'min-width:50px;max-width:50px;background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;border:1px solid #000000'},
            {'name': 'Tên hợp đồng', 'style': 'min-width:150px;background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;border:1px solid #000000'},
            {'name': 'Mã hợp đồng', 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;border:1px solid #000000'},
            {'name': 'Số hợp đồng', 'style': 'min-width:150px;background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;border:1px solid #000000'},
            {'name': 'Khối', 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;border:1px solid #000000'},
            {'name': 'Nhân sự phụ<br/>trách', 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;'},
            {'name': 'Khách hàng', 'style': 'min-width:200px;background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;'},
            {'name': 'Giai đoạn', 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;'},
            {'name': 'Giá trị hợp<br/>đồng', 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;'},
            {'name': 'Doanh thu xuất hóa đơn', 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;'},
            {'name': 'Công nợ đã thu', 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;'},
            {'name': 'Công nợ còn phải thu', 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;'},
            {'name': 'Lịch trình thanh<br/>toán', 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;'},
            {'name': 'Loại tiền', 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;'},
            {'name': 'Số tiền phải thanh toán', 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;'},
            {'name': 'Hóa đơn', 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;'},
            {'name': 'Ngày xuất hóa đơn', 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;'},
            {'name': 'Giá trị xuất hóa đơn', 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;'},
            {'name': 'Thời hạn thanh<br/>toán', 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;'},
            {'name': 'Ngày thanh<br/>toán dự kiến', 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;'},
            {'name': 'Ngày thanh<br/>toán thực tế', 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;'},
            {'name': 'Số ngày quá hạn', 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;'},
            {'name': 'Tỷ lệ thanh<br/>toán', 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;'},
            {'name': 'Hồ sơ thanh<br/>toán yêu cầu', 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;'}, ]
        return [columns_names]

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
        # date_from = min(fields.Date.from_string(options['date']['date_from']), fields.Date.from_string(options['date']['date_to']))
        # date_to = max(fields.Date.from_string(options['date']['date_from']), fields.Date.from_string(options['date']['date_to']))

        # datetime_from = datetime.combine(date_from, time.min)
        # datetime_to = datetime.combine(date_to, time.max)

        records = self.env['x.sale.contract'].search([])

        background = '#FFFFFF'
        with localcontext() as ctx:
            ctx.rounding = ROUND_HALF_UP
            for record in records:
                if background == '#FFFFFF':
                    background = '#D8DAE0'
                else:
                    background = '#FFFFFF'
                contract_columns = [
                    {'name': record.name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                    {'name': record.id or '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                    {'name': record.x_contract_code or '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                    {'name': record.en_team_id.display_name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                    {'name': record.user_id.display_name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    {'name': record.partner_id.display_name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                    {'name': dict(record.fields_get(['state'])['state']['selection'])[record.state] or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:normal;border:1px solid #000000'},
                    {'name': self.format_value(record.currency_id._convert(record.amount_total, self.env.company.currency_id, self.env.company, record.date_sign or fields.Datetime.now()), self.env.company.currency_id, True), 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                    {'name': self.format_value(sum(move.currency_id._convert(move.amount_total_signed, self.env.company.currency_id, self.env.company, move.invoice_date or fields.Datetime.now()) for move in record.move_ids), self.env.company.currency_id, True), 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                    {'name': self.format_value(sum(payment.currency_id._convert(payment.amount_company_currency_signed, self.env.company.currency_id, self.env.company, payment.date or fields.Datetime.now()) for payment in record.payment_ids), self.env.company.currency_id, True), 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                    {'name': self.format_value(sum(move.currency_id._convert(move.amount_total_signed, self.env.company.currency_id, self.env.company, move.invoice_date or fields.Datetime.now()) for move in record.move_ids) - sum(payment.currency_id._convert(payment.amount_company_currency_signed, self.env.company.currency_id, self.env.company, payment.date or fields.Datetime.now()) for payment in record.payment_ids), self.env.company.currency_id, True), 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                    {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                    {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                    {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                    {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                    {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                    {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                    {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                    {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                    {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                    {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                    {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                    {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                ]

                lines += [{
                    'id': 'contract_%s' % record.id,
                    'name': '',
                    'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000',
                    'level': 1,
                    'columns': contract_columns,
                    'unfoldable': True if record.x_payment_schedule_ids else False,
                    'unfolded': self._need_to_unfold('contract_%s' % record.id, options),
                }]
                for schedule in record.x_payment_schedule_ids:
                    schedule_columns = [
                        {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                        {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                        {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                        {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                        {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:normal;border:1px solid #000000'},
                        {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:normal;border:1px solid #000000'},
                        {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                        {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                        {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                        {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                        {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                        {'name': schedule.name, 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                        {'name': schedule.currency_id.display_name, 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                        {'name': self.format_value(schedule.x_cost, schedule.currency_id, True), 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                        {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                        {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                        {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                        {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                        {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                        {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                        {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                        {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                        {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                    ]

                    lines += [{
                        'id': 'schedule_%s' % schedule.id,
                        'name': '',
                        'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000',
                        'level': 2,
                        'parent_id': 'contract_%s' % record.id,
                        'columns': schedule_columns,
                        'unfoldable': True if schedule.invoice_ids else False,
                        'unfolded': self._need_to_unfold('schedule_%s' % schedule.id, options),
                    }]
                    for invoice in schedule.invoice_ids:
                        pay_term_lines = invoice.line_ids.filtered(lambda line: line.account_internal_type in ('receivable', 'payable'))
                        payments = self.env['account.payment'].search([('move_id', 'in', (pay_term_lines.matched_debit_ids.mapped('credit_move_id.move_id') | pay_term_lines.matched_credit_ids.mapped('credit_move_id.move_id')).ids)])
                        today = max(payments.mapped('date')) if payments else fields.Date.today()
                        invoice_date_due = invoice.invoice_date_due
                        if invoice.invoice_payment_term_id:
                            others_lines = invoice.line_ids.filtered(lambda line: line.account_id.user_type_id.type not in ('receivable', 'payable'))
                            company_currency_id = (invoice.company_id or self.env.company).currency_id
                            total_balance = sum(others_lines.mapped(lambda l: company_currency_id.round(l.balance)))
                            amount_residual = invoice.amount_residual
                            invoice_date_due = None
                            to_compute = invoice.invoice_payment_term_id.compute(total_balance, date_ref=invoice.invoice_date, currency=invoice.company_id.currency_id)
                            for to in to_compute:
                                if fields.Date.from_string(to[0]) > today:
                                    continue
                                total_balance -= to[1]
                                if amount_residual > abs(total_balance):
                                    invoice_date_due = max(fields.Date.from_string(to[0]), invoice_date_due) if invoice_date_due else fields.Date.from_string(to[0])
                        invoice_columns = [
                            {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                            {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                            {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                            {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                            {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:normal;border:1px solid #000000'},
                            {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:normal;border:1px solid #000000'},
                            {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                            {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                            {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                            {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                            {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                            {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                            {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                            {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                            {'name': invoice.display_name, 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                            {'name': invoice.invoice_date.strftime(lg.date_format) if invoice.invoice_date else '', 'class': 'date', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                            {'name': self.format_value(invoice.currency_id._convert(invoice.amount_total_in_currency_signed, self.env.company.currency_id, self.env.company, invoice.invoice_date or fields.Datetime.now()), self.env.company.currency_id, True), 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                            {'name': invoice.invoice_payment_term_id.display_name, 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                            {'name': invoice_date_due.strftime(lg.date_format) if invoice_date_due and not invoice.invoice_payment_term_id else '', 'class': 'date', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                            {'name': max(payments.mapped('date')).strftime(lg.date_format) if payments else '', 'class': 'date', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                            {'name': 0 if not invoice_date_due else max((today - invoice_date_due).days, 0), 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                            {'name': f'{Decimal((1 - invoice.amount_residual / invoice.amount_total_signed) * 100).to_integral_value(rounding=ROUND_HALF_UP) if invoice.amount_total_signed else 0}%', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                            {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                        ]
                        lines += [{
                            'id': 'invoice_%s' % invoice.id,
                            'name': '',
                            'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000',
                            'level': 3,
                            'parent_id': 'schedule_%s' % schedule.id,
                            'columns': invoice_columns,
                        }]
        return lines
