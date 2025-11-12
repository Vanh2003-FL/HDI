from odoo import fields, models, api


class SaleOrder(models.Model):
    _inherit = "sale.order"

    state = fields.Selection(selection_add=[
        ('to_approval', 'Trình duyệt'),
        ('approved', 'Đã duyệt'),
        ('sent',)],
        ondelete={'to_approval': lambda recs: recs.write({'state': 'draft'}), 'approved': lambda recs: recs.write({'state': 'draft'})})
    x_sale_contract_ids = fields.One2many('x.sale.contract', 'order_id', 'Hợp đồng')
    contract_count = fields.Integer(string='Hợp đồng', compute='_compute_contract_count', compute_sudo=True)

    @api.depends('x_sale_contract_ids')
    def _compute_contract_count(self):
        for rec in self:
            rec.contract_count = len(rec.x_sale_contract_ids)

    def action_create_contract(self):
        self.ensure_one()
        sum = discount = 0
        for line in self.order_line:
            sum += line.price_unit * line.product_uom_qty
            discount += line.discount / 100 * line.price_unit * line.product_uom_qty
        return {
            'name': 'Tạo hợp đồng',
            'view_mode': 'form',
            'res_model': 'x.sale.contract',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'view_id': self.env.ref('ngsd_crm.sale_contract_form').id,
            'context': {
                'default_partner_id': self.partner_id.id,
                'default_x_payment_address': self.partner_invoice_id.id,
                'default_x_delivery_address': self.partner_shipping_id.id,
                'default_currency_id': self.currency_id.id,
                'default_x_money': sum,
                'default_x_discount': discount,
                'default_x_cost_discount': self.amount_untaxed,
                'default_x_tax': self.amount_tax,
                'default_x_total_cost': self.amount_total,
                'default_order_id': self.id,
                'default_line_ids': [(0, 0, {'product_id': line.product_id.id, 'name': line.name, 'product_uom_qty': line.product_uom_qty, 'price_unit': line.price_unit, 'tax_id': [(6, 0, line.tax_id.ids)], 'discount': line.discount}) for line in self.order_line]
            }
        }

    def to_contract(self):
        return self.open_form_or_tree_view('ngsd_crm.action_sale_contract', False, self.x_sale_contract_ids, {'create': False, 'edit': False})
