# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ShippingOrderPrintWizard(models.TransientModel):
    _name = 'shipping.order.print.wizard'
    _description = 'Wizard để in đơn hàng gửi'

    order_ids = fields.Many2many('shipping.order', string='Đơn hàng', required=True)
    order_count = fields.Integer(string='Số đơn', compute='_compute_order_count')
    print_type = fields.Selection([
        ('single', 'In từng đơn riêng'),
        ('batch', 'In gộp nhiều đơn'),
    ], string='Kiểu in', default='batch', required=True)

    @api.depends('order_ids')
    def _compute_order_count(self):
        for wizard in self:
            wizard.order_count = len(wizard.order_ids)

    @api.model
    def default_get(self, fields):
        """Get default values from context"""
        res = super().default_get(fields)
        active_ids = self.env.context.get('active_ids', [])
        if active_ids:
            res['order_ids'] = [(6, 0, active_ids)]
        return res

    def action_print(self):
        """Print shipping orders"""
        self.ensure_one()
        
        if not self.order_ids:
            raise UserError(_('Vui lòng chọn ít nhất một đơn hàng để in!'))
        
        # Return report action
        return self.env.ref('hdi_shipping.action_report_shipping_order').report_action(self.order_ids)

    def action_print_and_close(self):
        """Print and close wizard"""
        self.action_print()
        return {'type': 'ir.actions.act_window_close'}
