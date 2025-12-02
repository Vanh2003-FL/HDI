# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ShippingOrderStateLog(models.Model):
    _name = 'shipping.order.state.log'
    _description = 'Shipping Order State Change Log'
    _order = 'change_date desc, id desc'
    _rec_name = 'order_id'

    order_id = fields.Many2one('shipping.order', string='Đơn hàng', required=True, ondelete='cascade', index=True)
    user_id = fields.Many2one('res.users', string='Người thực hiện', required=True)
    old_state = fields.Selection([
        ('draft', 'Đơn nháp'),
        ('waiting_pickup', 'Chờ lấy hàng'),
        ('in_transit', 'Đang vận chuyển'),
        ('pending_return_approval', 'Chờ duyệt hoàn'),
        ('delivered', 'Đã giao'),
        ('returned', 'Đã hoàn'),
        ('cancelled', 'Đã hủy'),
    ], string='Trạng thái cũ', required=True)
    new_state = fields.Selection([
        ('draft', 'Đơn nháp'),
        ('waiting_pickup', 'Chờ lấy hàng'),
        ('in_transit', 'Đang vận chuyển'),
        ('pending_return_approval', 'Chờ duyệt hoàn'),
        ('delivered', 'Đã giao'),
        ('returned', 'Đã hoàn'),
        ('cancelled', 'Đã hủy'),
    ], string='Trạng thái mới', required=True)
    change_date = fields.Datetime(string='Thời gian', required=True, default=fields.Datetime.now, index=True)
    note = fields.Text(string='Ghi chú')

    # Display fields
    old_state_display = fields.Char(string='Từ trạng thái', compute='_compute_state_display', store=False)
    new_state_display = fields.Char(string='Đến trạng thái', compute='_compute_state_display', store=False)

    @api.depends('old_state', 'new_state')
    def _compute_state_display(self):
        state_dict = dict(self._fields['old_state'].selection)
        for log in self:
            log.old_state_display = state_dict.get(log.old_state, '')
            log.new_state_display = state_dict.get(log.new_state, '')
