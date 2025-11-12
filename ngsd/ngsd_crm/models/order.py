from odoo import *


class AccountMove(models.Model):
    _inherit = 'account.move'
    invoice_payment_term_id = fields.Many2one(compute='_compute_invoice_payment_term_id', store=True, readonly=False)

    @api.depends('schedule_id')
    def _compute_invoice_payment_term_id(self):
        for rec in self:
            invoice_payment_term_id = rec.invoice_payment_term_id
            if rec.schedule_id:
                invoice_payment_term_id = rec.schedule_id.payment_term_id
            rec.invoice_payment_term_id = invoice_payment_term_id

    contract_id = fields.Many2one(string='Hợp đồng', comodel_name='x.sale.contract')
    annex_id = fields.Many2one(string='Phụ lục hợp đồng', comodel_name='x.sale.contract.annex', domain="[('order_id','=',contract_id)]")
    stage = fields.Char(string='Giai đoạn')
    x_payment_schedule_ids = fields.One2many(related='contract_id.x_payment_schedule_ids')
    schedule_id = fields.Many2one(string='Giai đoạn', comodel_name='x.payment.schedule', domain="[('id','in',x_payment_schedule_ids)]")


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    x_contract_id = fields.Many2one(string='Hợp đồng', comodel_name='x.sale.contract')


class Order(models.Model):
    _name = 'x.order'
    _description = 'Đơn hàng'

    def create_account_move(self):
        self.env['account.move'].create({
            'partner_id': self.partner_id.id,
            'move_type': 'out_invoice',
            'invoice_date': self.order_date,
            'currency_id': self.currency_id.id,
            'contract_id': self.contract_id.id,
            'annex_id': self.annex_id.id,
            'stage': self.payment_schedule_id.name,
            'invoice_line_ids': [(0, 0, {
                'name': self.payment_schedule_id.name,
                'quantity': 1,
                'tax_ids': [(5, 0, 0)],
                'price_unit': self.amount, })]
        })
        return {
            'effect': {
                'fadeout': 'slow',
                'message': '!',
                'img_url': '/web/image/%s/%s/image_1024' % (self.env.user._name, self.env.user.id) if self.env.user.image_1024 else '/web/static/img/smile.svg',
                'type': 'rainbow_man',
            }
        }

    def do(self):
        self.write({'order_date': fields.Date.today(), 'amount': self.payment_schedule_id.x_cost, 'currency_id': self.contract_id.currency_id})
        return {"type": "ir.actions.act_window_close"}

    name = fields.Char(string='Tên', default='Mới')
    contract_id = fields.Many2one(string='Hợp đồng', comodel_name='x.sale.contract')
    annex_id = fields.Many2one(string='Phụ lục hợp đồng', comodel_name='x.sale.contract.annex', domain="[('order_id','=',contract_id)]")
    partner_id = fields.Many2one(string='Khách hàng', comodel_name='res.partner', related='contract_id.partner_id')
    order_date = fields.Date(string='Ngày đơn hàng')
    payment_schedule_id = fields.Many2one(comodel_name='x.payment.schedule', string='Lịch thanh toán', domain="[('x_sale_contract_id','=',contract_id)]")
    amount = fields.Monetary(string='Giá trị đơn hàng', default=0)
    currency_id = fields.Many2one(string='Tiền tệ', comodel_name='res.currency', default=lambda self: self.env.company.currency_id)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == 'Mới':
                vals['name'] = self.env['ir.sequence'].next_by_code('x.order') or 'Mới'
        return super().create(vals_list)
