from odoo import models, fields, api


class KpiDetail(models.Model):
    _name = 'en.kpi.detail'
    _description = 'KPI phân bổ'

    year = fields.Char(string='Năm', compute_sudo=True, compute='_compute_year', store=True)

    @api.depends('date_from')
    def _compute_year(self):
        for rec in self:
            rec.year = str(rec.date_from.year)

    name = fields.Char(string='Tên')
    kpi_id = fields.Many2one(string='KPI', comodel_name='en.kpi.kpi')
    line_kpi_id = fields.Many2one(string='KPI', comodel_name='en.kpi.line')
    type = fields.Selection(string='Loại', selection=[('team', 'Nhóm kinh doanh'), ('sale', 'Nhân viên kinh doanh')])
    sale_team_id = fields.Many2one(string='Nhóm kinh doanh', comodel_name='crm.team')
    user_id = fields.Many2one(string='Nhân viên kinh doanh', comodel_name='res.users')
    date_from = fields.Date(string='Từ ngày')
    date_to = fields.Date(string='Đến ngày')
    rate = fields.Float(string='Tỷ lệ phân bổ', default=0)
    currency_id = fields.Many2one(string='Tiền tệ', comodel_name='res.currency')
    kpi_sales = fields.Float(string='Chỉ tiêu doanh số', default=0)
    kpi_revenue = fields.Float(string='Chỉ tiêu dòng tiền', default=0)
    kpi_invoiced = fields.Float(string='Chỉ tiêu doanh thu', default=0)
    expected_sales = fields.Float(string='Kế hoạch doanh số', default=0)
    expected_revenue = fields.Float(string='Kế hoạch dòng tiền', default=0)
    expected_invoiced = fields.Float(string='Kế hoạch doanh thu', default=0)
    sales = fields.Float(string='Thực tế doanh số', default=0)
    revenue = fields.Float(string='Thực tế dòng tiền', default=0)
    invoiced = fields.Float(string='Thực tế doanh thu', default=0)

    def read(self, fields=None, load='_classic_read'):
        self.recompute_many_fields()
        return super().read(fields=fields, load=load)

    def recompute_many_fields(self):
        self = self.sudo()
        for rec in self:
            name = f'{rec.user_id.name if rec.type == "sale" else rec.sale_team_id.name} {rec.date_from.strftime("%m/%Y") if rec.date_from else ""}'

            if rec.type == "sale":
                expected_sales = sum(x.company_currency._convert(x.ngsd_revenue, rec.currency_id, rec.kpi_id.company_id or x.company_id or self.env.company, x.date_deadline) for x in self.env['crm.lead'].search([('user_id', '=', rec.user_id.id), ('active', '=', True), ('date_deadline', '<=', rec.date_to), ('date_deadline', '>=', rec.date_from)]))
                expected_revenue = sum(x.currency_id._convert(x.amount, rec.currency_id, rec.kpi_id.company_id or x.lead_id.company_id or self.env.company, x.date) for x in self.env['x.crm.lead.payment'].search([('lead_id.user_id', '=', rec.user_id.id), ('lead_id.active', '=', True), ('date', '<=', rec.date_to), ('date', '>=', rec.date_from)]))
                expected_invoiced = sum(x.currency_id._convert(x.amount, rec.currency_id, rec.kpi_id.company_id or x.lead_id.company_id or self.env.company, x.date) for x in self.env['x.crm.lead.invoice'].search([('lead_id.user_id', '=', rec.user_id.id), ('lead_id.active', '=', True), ('date', '<=', rec.date_to), ('date', '>=', rec.date_from)]))
                sales = sum(x.currency_id._convert(x.fixed_amount_total, rec.currency_id, rec.kpi_id.company_id or self.env.company, x.x_date_start) for x in self.env['x.sale.contract'].search([('user_id', '=', rec.user_id.id), ('state', '=', 'done'), ('x_date_start', '<=', rec.date_to), ('x_date_start', '>=', rec.date_from)]))
                revenue = sum(x.currency_id._convert(x.amount, rec.currency_id, rec.kpi_id.company_id or x.company_id or self.env.company, x.date) for x in self.env['account.payment'].search([('reconciled_invoice_ids.invoice_user_id', '=', rec.user_id.id), ('state', '=', 'posted'), ('date', '<=', rec.date_to), ('date', '>=', rec.date_from)]))
                invoiced = sum(x.currency_id._convert(x.amount_total, rec.currency_id, rec.kpi_id.company_id or x.company_id or self.env.company, x.invoice_date) for x in self.env['account.move'].search([('invoice_user_id', '=', rec.user_id.id), ('state', '=', 'posted'), ('invoice_date', '<=', rec.date_to), ('invoice_date', '>=', rec.date_from)]))
            elif rec.type == "team":
                expected_sales = sum(x.company_currency._convert(x.ngsd_revenue, rec.currency_id, rec.kpi_id.company_id or x.company_id or self.env.company, x.date_deadline) for x in self.env['crm.lead'].search([('team_id', '=', rec.sale_team_id.id), ('active', '=', True), ('date_deadline', '<=', rec.date_to), ('date_deadline', '>=', rec.date_from)]))
                expected_revenue = sum(x.currency_id._convert(x.amount, rec.currency_id, rec.kpi_id.company_id or x.lead_id.company_id or self.env.company, x.date) for x in self.env['x.crm.lead.payment'].search([('lead_id.team_id', '=', rec.sale_team_id.id), ('lead_id.active', '=', True), ('date', '<=', rec.date_to), ('date', '>=', rec.date_from)]))
                expected_invoiced = sum(x.currency_id._convert(x.amount, rec.currency_id, rec.kpi_id.company_id or x.lead_id.company_id or self.env.company, x.date) for x in self.env['x.crm.lead.invoice'].search([('lead_id.team_id', '=', rec.sale_team_id.id), ('lead_id.active', '=', True), ('date', '<=', rec.date_to), ('date', '>=', rec.date_from)]))
                sales = sum(x.currency_id._convert(x.fixed_amount_total, rec.currency_id, rec.kpi_id.company_id or self.env.company, x.x_date_start) for x in self.env['x.sale.contract'].search([('user_id.team_id', '=', rec.sale_team_id.id), ('state', '=', 'done'), ('x_date_start', '<=', rec.date_to), ('x_date_start', '>=', rec.date_from)]))
                revenue = sum(x.currency_id._convert(x.amount, rec.currency_id, rec.kpi_id.company_id or x.company_id or self.env.company, x.date) for x in self.env['account.payment'].search([('reconciled_invoice_ids.invoice_user_id.team_id', '=', rec.sale_team_id.id), ('state', '=', 'posted'), ('date', '<=', rec.date_to), ('date', '>=', rec.date_from)]))
                invoiced = sum(x.currency_id._convert(x.amount_total, rec.currency_id, rec.kpi_id.company_id or x.company_id or self.env.company, x.invoice_date) for x in self.env['account.move'].search([('invoice_user_id.team_id', '=', rec.sale_team_id.id), ('state', '=', 'posted'), ('invoice_date', '<=', rec.date_to), ('invoice_date', '>=', rec.date_from)]))
            else:
                expected_sales = expected_revenue = expected_invoiced = sales = revenue = invoiced = 0
            rec.write(dict(name=name, expected_sales=expected_sales, expected_revenue=expected_revenue, expected_invoiced=expected_invoiced, sales=sales, revenue=revenue, invoiced=invoiced))
