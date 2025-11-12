from odoo import models, fields, api, _, exceptions
import datetime
from odoo.exceptions import UserError


class Contract(models.Model):
    _name = 'x.sale.contract'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Hợp đồng'

    def read(self, fields=None, load='_classic_read'):
        for rec in self:
            if rec.state == 'done' and rec.x_date_end and datetime.date.today() > rec.x_date_end:
                rec.write({'state': 'expired'})
        return super().read(fields, load)

    en_team_id = fields.Many2one(string='Đội kinh doanh', comodel_name='crm.team')

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        if any('amount_total_change' in vals for vals in vals_list):
            res._compute_fixed_amount_total()
        # if 'order_line' in vals_list:
        #     res.recompute_x_date_end()
        return res

    def write(self, vals):
        res = super().write(vals)
        if 'amount_total_change' in vals:
            self._compute_fixed_amount_total()
        # if 'order_line' in vals:
        #     self.recompute_x_date_end()
        return res

    fixed_amount_total = fields.Monetary(string='Giá trị hợp đồng điều chỉnh', store=True, copy=False)

    def _compute_fixed_amount_total(self):
        for rec in self:
            a = rec.order_line.filtered(lambda x: x.change == 'value')
            if a:
                a = a.sorted(lambda x: x.id, reverse=True)[0]
            b = rec.order_line.filtered(lambda x: x.change == 'addition')
            rec.fixed_amount_total = (a.contract_value if a else rec.amount_total) + sum(b.mapped('contract_value'))

    fixed_date_end = fields.Date(string='Thời hạn hợp đồng điều chỉnh', readonly=True, copy=False)

    def _compute_fixed_date_end(self):
        for rec in self:
            a = rec.order_line.filtered(lambda x: x.change == 'duration')
            if a:
                a = a.sorted(lambda x: x.id, reverse=True)[0]
            rec.fixed_date_end = a.contract_date

    payment_ids = fields.One2many(string='Thanh toán', comodel_name='account.payment', inverse_name='x_contract_id')
    payment_count = fields.Integer(string='Thanh toán', compute='_compute_payment_count', compute_sudo=True)

    @api.depends('payment_ids')
    def _compute_payment_count(self):
        for rec in self:
            rec.payment_count = len(rec.payment_ids)

    def create_payment(self):
        ctx = {'default_move_journal_types': ['bank'], 'default_date': fields.Date.today(), 'default_partner_id': self.partner_id.id, 'default_x_contract_id': self.id, 'default_ref': self.name}
        return self.open_form_or_tree_view('account.action_account_payments', False, False, ctx, 'Tạo thanh toán', 'new')

    def to_payment(self):
        ctx = {'default_move_journal_types': ['bank'], 'default_date': fields.Date.today(), 'default_partner_id': self.partner_id.id, 'default_x_contract_id': self.id, 'default_ref': self.name, 'create': False}
        return self.open_form_or_tree_view('account.action_account_payments', False, self.payment_ids, ctx)

    move_ids = fields.One2many(string='Hóa đơn', comodel_name='account.move', inverse_name='contract_id')
    move_count = fields.Integer(string='Hóa đơn', compute='_compute_move_count', compute_sudo=True)

    @api.depends('move_ids')
    def _compute_move_count(self):
        for rec in self:
            rec.move_count = len(rec.move_ids)

    def create_invoice(self):
        ctx = {'default_move_type': 'out_invoice', 'default_partner_id': self.partner_id.id, 'default_contract_id': self.id, 'default_user_id': self.user_id.id}
        return self.open_form_or_tree_view('account.action_move_out_invoice_type', False, False, ctx, 'Tạo hóa đơn', 'new')

    def to_invoice(self):
        ctx = {'default_move_type': 'out_invoice', 'create': False, 'default_partner_id': self.partner_id.id, 'default_contract_id': self.id, 'default_user_id': self.user_id.id}
        return self.open_form_or_tree_view('account.action_move_out_invoice_type', False, self.move_ids, ctx)

    lead_id = fields.Many2one(string='Tiềm năng', comodel_name='crm.lead', readonly=True, copy=False)

    def create_order(self):
        return self.open_form_or_tree_view('ngsd_crm.order_act', 'ngsd_crm.order_simplied_form', False, {'default_contract_id': self.id}, 'Tạo đơn hàng', 'new')

    name = fields.Char('Tên hợp đồng', required=True, copy=False, index=True)
    x_contract_code = fields.Char('Số hợp đồng', copy=False, readonly=False, required=True)
    state = fields.Selection([
        ("draft", "Mới"),
        ("done", "Đã xác nhận"),
        ("expired", "Đã hết hạn"),
        ("cancel", "Hủy"),
    ], default='draft', string='Trạng thái', required=True)
    user_ids = fields.Many2many(string='Người duyệt', comodel_name='res.users')

    def button_done(self):
        self.write({'state': 'done'})

    def button_over(self):
        self.write({'state': 'cancel'})

    partner_id = fields.Many2one('res.partner', string='Khách hàng', required=True, domain="[('is_customer', '=', True)]")
    x_payment_method = fields.Selection([
        ('tm', 'Tiền mặt'),
        ('ck', 'Chuyển khoản')], string="Phương thức thanh toán", default='tm')
    x_payment_state = fields.Selection([
        ('no', 'Chưa thanh toán'),
        ('yes', 'Đã thanh toán')], string="Trạng thái thanh toán", default='no')
    x_date_start = fields.Date('Ngày hiệu lực', default=lambda self: fields.Date.today(), required=True, tracking=True)
    x_date_end = fields.Date('Ngày hết hiệu lực', required=True, compute=False, store=True, readonly=False, tracking=True)

    @api.onchange('change_x_date_end')
    def recompute_x_date_end(self):
        for rec in self:
            x_date_end = False
            for l in rec.order_line:
                if any(change.en_change == 'change_time' for change in l.change_ids) and l.contract_date:
                    x_date_end = l.contract_date
            if x_date_end:
                rec.x_date_end = x_date_end

    # thêm trường để onchange ngày hết hiệu lực
    change_x_date_end = fields.Date(compute='get_change_x_date_end')

    @api.depends('order_line', 'order_line.change_ids', 'order_line.contract_date')
    def get_change_x_date_end(self):
        for rec in self:
            x_date_end = False
            for l in rec.order_line:
                if any(change.en_change == 'change_time' for change in l.change_ids) and l.contract_date:
                    x_date_end = l.contract_date
            rec.change_x_date_end = x_date_end

    x_period_date = fields.Date('Kỳ hạn')
    user_id = fields.Many2one(comodel_name='res.users', string="Nhân viên kinh doanh", default=lambda self: self.env.user, required=True)
    x_noti_date = fields.Integer(string='Thông báo trước khi hết hạn (số ngày)', default=0)
    x_payment_address = fields.Many2one(string='Địa chỉ thanh toán', comodel_name='res.partner')
    x_delivery_address = fields.Many2one(string='Địa chỉ giao hàng', comodel_name='res.partner')
    x_bill_recipient_id = fields.Many2one('res.partner', string='Người nhận hóa đơn')
    x_receiver_id = fields.Many2one('res.partner', string='Người nhận hàng')
    x_special_term = fields.Text('Thuật ngữ đặc biệt')
    x_note = fields.Text('Mô tả')
    x_representative_customer_id = fields.Many2one('res.partner', string='Người đại diện ký bên khách hàng')
    x_representative_customer = fields.Char(string='Người đại diện ký bên khách hàng')
    x_representative_firm_id = fields.Many2one('res.partner', string='Người đại diện ký bên công ty')
    position_customer = fields.Char(compute='_get_position_customer', store=True, string='Chức vụ', readonly=False)
    position_firm = fields.Char(compute='_get_position_firm', store=True, string='Chức vụ', readonly=False)

    @api.depends('x_representative_customer_id')
    def _get_position_customer(self):
        for rec in self:
            rec.position_customer = rec.x_representative_customer_id.function

    @api.depends('x_representative_firm_id')
    def _get_position_firm(self):
        for rec in self:
            rec.position_firm = rec.x_representative_firm_id.function

    x_date_customer = fields.Date(string='Ngày ký')
    x_date_firm = fields.Date(string='Ngày ký')
    order_id = fields.Many2one('sale.order', string='Báo giá')
    x_money = fields.Float(string='Thành tiền', default=0)
    x_discount = fields.Float(string='Chiết khấu', default=0)
    x_cost_discount = fields.Monetary(string='Giá sau chiết khấu')
    currency_id = fields.Many2one('res.currency', string='Tiền tệ', required=True, default=lambda self: self.env.company.currency_id)
    x_tax = fields.Float(string='Thuế (%)', default=0)
    x_delivery_cost = fields.Monetary(string='Phí vận chuyển')
    x_total_cost = fields.Monetary(string='Tổng')
    x_payment_schedule_ids = fields.One2many('x.payment.schedule', 'x_sale_contract_id', 'Lịch trình thanh toán')

    @api.constrains('x_payment_schedule_ids')
    def _constrains_payment_schedule_max_percent(self):
        if any(sum(rec.x_payment_schedule_ids.mapped('x_percent')) > 1 for rec in self):
            raise exceptions.ValidationError("Tổng tỷ lệ các giai đoạn thanh toán > 100%")

    order_line = fields.One2many(string='Phụ lục hợp đồng', comodel_name='x.sale.contract.annex', inverse_name='order_id')
    x_project_type_id = fields.Many2one('project.type.source', string="Loại hợp đồng")
    sellerPid = fields.Many2one('res.partner', string='Đơn vị bán', domain="[('is_supplier', '=', True), ('parent_id', '=', False)]")
    amount_untaxed = fields.Monetary(string='Giá trị hợp đồng (trước thuế)', store=True, compute='_amount_all')
    amount_tax = fields.Monetary(string='Thuế VAT', store=True, compute='_amount_all')
    amount_total = fields.Monetary(string='Giá trị hợp đồng (sau thuế)', store=True, compute='_amount_all', tracking=True)
    amount_total_change = fields.Monetary(string='Giá trị hợp đồng (sau thuế) thay đổi', store=True, compute='_get_amount_total_change', tracking=True)
    total_contract_value = fields.Float(string='Tổng Giá trị thay đổi', store=True, compute='_get_amount_total_change')

    @api.depends('line_ids.price_total')
    def _amount_all(self):
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.line_ids:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            order.update({
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_total': amount_untaxed + amount_tax,
            })

    @api.depends('order_line.contract_value', 'order_line.change_ids', 'amount_total')
    def _get_amount_total_change(self):
        for rec in self:
            rec.total_contract_value = sum(rec.order_line.filtered(lambda l: l.has_add_value or l.has_reduce_value).mapped('contract_value'))
            rec.amount_total_change = rec.amount_total + rec.total_contract_value

    rate = fields.Float(string='Tỷ giá', compute='_compute_currency_rate', compute_sudo=True, store=True, readonly=True)
    company_id = fields.Many2one(string='Công ty', comodel_name='res.company', default=lambda self: self.env.company, required=True)

    @api.depends('currency_id', 'date_sign', 'company_id')
    def _compute_currency_rate(self):
        for order in self:
            if not order.company_id:
                order.rate = order.currency_id.with_context(date=order.date_sign).rate or 1.0
                continue
            elif order.company_id.currency_id and order.currency_id:  # the following crashes if any one is undefined
                order.rate = self.env['res.currency']._get_conversion_rate(order.company_id.currency_id, order.currency_id, order.company_id, order.date_sign or fields.Date.today())
            else:
                order.rate = 1.0

    date_sign = fields.Date(string='Ngày ký', required=True)
    line_ids = fields.One2many(string='Hàng hoá dịch vụ', comodel_name='x.sale.contract.line', inverse_name='line_id')
    guarantee_ids = fields.One2many(string='Bảo lãnh', comodel_name='x.sale.contract.guarantee', inverse_name='guarantee_id')

    # @api.model
    # def create(self, vals):
    #     vals['name'] = self.env['ir.sequence'].next_by_code('sale.contract.code') or 'Mới'
    #     return super().create(vals)

    en_sales_sp_id = fields.Many2one('res.users', string='Sales Support')


class SaleContractLine(models.Model):
    _name = 'x.sale.contract.line'
    _description = 'Hàng hoá dịch vụ'

    line_id = fields.Many2one(string='hàng hoá', comodel_name='x.sale.contract', required=True, ondelete='cascade')
    product_id = fields.Many2one(comodel_name='product.product', string='Sản phẩm')
    name = fields.Char(string='Mô tả')
    product_uom_qty = fields.Float(string='Số lượng', default=1)
    price_unit = fields.Float(string='Đơn giá', default=0)
    tax_id = fields.Many2many(comodel_name='account.tax', string='Thuế', domain=[('type_tax_use', '=', 'sale')])
    discount = fields.Float(string='CK.%', default=0)

    currency_id = fields.Many2one(related='line_id.currency_id')
    price_subtotal = fields.Monetary(compute='_compute_amount', string='Thành tiền', store=True)
    price_tax = fields.Float(compute='_compute_amount', string='Tổng thuế', store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Thành tiền', store=True)

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id')
    def _compute_amount(self):
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.tax_id.compute_all(price, line.line_id.currency_id, line.product_uom_qty, product=line.product_id)
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })


class SaleContractGuarantee(models.Model):
    _name = 'x.sale.contract.guarantee'
    _description = 'Bảo lãnh'

    guarantee_id = fields.Many2one(string='bảo lãnh', comodel_name='x.sale.contract', required=True, ondelete='cascade')
    en_guarantee_id = fields.Many2one(string='Tên bảo lãnh', comodel_name='en.guarantee', required=True)
    code = fields.Char(string='Số bảo lãnh', required=True)
    currency_id = fields.Many2one('res.currency', string='Tiền tệ', default=lambda self: self.env.company.currency_id)
    name = fields.Char(string='Tên bảo lãnh', required=False)
    bank_id = fields.Many2one(string='Ngân hàng', comodel_name='res.bank')
    amount = fields.Float(string='Giá trị được bảo lãnh', default=0)
    date = fields.Date(string='Ngày phát hành')
    date_start = fields.Date(string='Ngày hiệu lực', required=True)
    date_end = fields.Date(string='Ngày hết hiệu lực')
    date_extend = fields.Date(string='Ngày gia hạn')
    remind_day = fields.Integer(string='Thông báo trước khi hết hạn(số ngày)', default=0)
    note = fields.Text(string='Ghi chú')

    def re_create_guarantee(self):
        need_create = self.search([('name', '!=', False), ('en_guarantee_id', '=', False)])
        for rec in need_create:
            rec.en_guarantee_id = self.env['en.guarantee'].create({'name': rec.name})


class ContractAnnex(models.Model):
    _name = 'x.sale.contract.annex'
    _description = 'Phụ lục hợp đồng'

    name = fields.Char(string='Tên')
    order_id = fields.Many2one(string='Hợp đồng', comodel_name='x.sale.contract', required=True, ondelete='cascade')
    change = fields.Selection(string='Loại thay đổi', selection=[
        ('duration', 'Thay đổi thời hạn'),
        ('value', 'Thay đổi giá trị'),
        ('addition', 'Cộng thêm giá trị'),
        ('article', 'Thay đổi điều khoản'),
    ])

    change_ids = fields.Many2many('en.change', string='Loại thay đổi')

    contract_date = fields.Date(string='Thời hạn hợp đồng')
    contract_value = fields.Float(string='Giá trị thay đổi', default=0)
    description = fields.Text(string='Mô tả')

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        if any('change_ids' in vals or 'contract_date' in vals or 'contract_value' in vals for vals in vals_list):
            res.order_id._compute_fixed_amount_total()
            res.order_id._compute_fixed_date_end()
        return res

    def write(self, vals):
        res = super().write(vals)
        if 'change_ids' in vals or 'contract_date' in vals or 'contract_value' in vals:
            self.order_id._compute_fixed_amount_total()
            self.order_id._compute_fixed_date_end()
        return res

    def unlink(self):
        order_ids = self.mapped('order_id')
        res = super().unlink()
        order_ids._compute_fixed_amount_total()
        order_ids._compute_fixed_date_end()
        return res

    attachment_ids = fields.Many2many('ir.attachment', string='File')

    def fill_en_change_ids_old_data(self):
        # Cộng thêm giá trị (change) = Cộng thêm giá trị (en_change_ids)
        # Thay đổi thời hạn (change) = Thay đổi thời gian (en_change_ids)
        # Thay đổi giá trị (change) = Cộng thêm giá trị (en_change_ids)
        # Thay đổi điều khoản (change) = Thay đổi điều khoản (en_change_ids)
        self.search([('change', '=', 'duration'), ('change_ids', '=', False)]).write({'change_ids': self.env['en.change'].search([('en_change', '=', 'change_time')]).ids})
        self.search([('change', '=', 'addition'), ('change_ids', '=', False)]).write({'change_ids': self.env['en.change'].search([('en_change', '=', 'add_value')]).ids})
        self.search([('change', '=', 'value'), ('change_ids', '=', False)]).write({'change_ids': self.env['en.change'].search([('en_change', '=', 'add_value')]).ids})
        self.search([('change', '=', 'article'), ('change_ids', '=', False)]).write({'change_ids': self.env['en.change'].search([('en_change', '=', 'change_terms')]).ids})

    has_add_value = fields.Boolean(compute='_get_lst_en_change')
    has_reduce_value = fields.Boolean(compute='_get_lst_en_change')
    has_change_time = fields.Boolean(compute='_get_lst_en_change')
    has_change_terms = fields.Boolean(compute='_get_lst_en_change')
    has_other = fields.Boolean(compute='_get_lst_en_change')

    @api.depends('change_ids')
    def _get_lst_en_change(self):
        fs = ['add_value', 'reduce_value', 'change_time', 'change_terms', 'other']
        for rec in self:
            for f in fs:
                rec['has_' + f] = rec.change_ids and any(change.en_change == f for change in rec.change_ids)

    @api.onchange('has_reduce_value', 'has_add_value', 'contract_value')
    def choose_has_reduce_value(self):
        rate = 0
        if self.has_add_value:
            rate = 1
        if self.has_reduce_value:
            rate = -1
        if self.contract_value != rate * abs(self.contract_value):
            self.contract_value = rate * abs(self.contract_value)

    @api.constrains('change_ids')
    def check_only_one_type_change_value(self):
        for rec in self:
            if rec.has_add_value and rec.has_reduce_value:
                raise UserError('Không thể chọn phụ lục vừa cộng thêm giá trị, vừa giảm giá trị!')


class ENChange(models.Model):
    _name = 'en.change'
    _description = 'Loại thay đổi'

    name = fields.Char(required=1)
    en_change = fields.Selection([('add_value', 'Cộng thêm giá trị'), ('reduce_value', 'Giảm giá trị'), ('change_time', 'Thay đổi thời gian'), ('change_terms', 'Thay đổi điều khoản'), ('other', 'Khác')], string='Loại thay đổi', required=1)


class ENGuarantee(models.Model):
    _name = 'en.guarantee'
    _description = 'Tên bảo lãnh'

    name = fields.Char('Tên bảo lãnh', required=1)
