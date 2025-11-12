from odoo import models, fields, api, _, exceptions


class Contact(models.Model):
    _name = 'x.payment.schedule'
    _description = 'Lịch trình thanh toán'

    invoice_ids = fields.One2many(string='Hóa đơn', comodel_name='account.move', inverse_name='schedule_id')
    sequence = fields.Integer(string="STT", default=10)
    name = fields.Char('Tên giai đoạn', copy=False, index=True, default=False, readonly=False)
    x_percent = fields.Float('Tỉ lệ giá trị trên hợp đồng', store=True, readonly=False, compute='_compute_x_percent')
    x_cost = fields.Float('Giá trị giai đoạn', store=True, readonly=False, compute="compute_x_cost")
    currency_id = fields.Many2one('res.currency', string='Tiền tệ', default=lambda self: self.env.company.currency_id, required=True)
    x_sale_contract_id = fields.Many2one('x.sale.contract', string='Hợp đồng', required=True, ondelete='cascade')
    x_total = fields.Monetary(string='Tổng', related="x_sale_contract_id.x_total_cost")
    payment_term_id = fields.Many2one('account.payment.term', string='Điều khoản thanh toán')
    due_date = fields.Date(string='Ngày bắt đầu tính công nợ')
    payment_date = fields.Date(string='Ngày dự kiến thanh toán')
    required_document = fields.Text(string='Hồ sơ cần thiết')
    note = fields.Char(string='Ghi chú')

    @api.depends('x_cost', 'x_sale_contract_id.amount_total')
    def _compute_x_percent(self):
        for rec in self:
            rec.x_percent = rec.x_cost / rec.x_sale_contract_id.amount_total_change if rec.x_sale_contract_id.amount_total_change else 0

    @api.depends('x_percent', 'x_sale_contract_id.amount_total')
    def compute_x_cost(self):
        for rec in self:
            rec.x_cost = rec.x_sale_contract_id.amount_total_change * rec.x_percent

    @api.onchange('name')
    def onchange_get_name(self):
        if not self.name:
            self.name = f'Lần %s_'%(len(self.x_sale_contract_id.x_payment_schedule_ids))
