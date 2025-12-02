from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime


class ShippingOrder(models.Model):
    _name = 'shipping.order'
    _description = 'Shipping Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'order_number'
    _order = 'created_date desc, id desc'

    # Order information
    order_number = fields.Char(string='Mã đơn hàng', readonly=True, copy=False)
    state = fields.Selection([
        ('draft', 'Đơn nháp'),
        ('waiting_pickup', 'Chờ lấy hàng'),
        ('in_transit', 'Đang vận chuyển'),
        ('pending_return_approval', 'Chờ duyệt hoàn'),
        ('delivered', 'Đã giao'),
        ('returned', 'Đã hoàn'),
        ('cancelled', 'Đã hủy'),
    ], string='Trạng thái', default='draft', tracking=True, required=True)
    
    created_date = fields.Datetime(string='Ngày tạo', readonly=True, default=fields.Datetime.now, index=True)
    user_id = fields.Many2one('res.users', string='Người tạo', readonly=True, default=lambda self: self.env.user)
    approved_date = fields.Datetime(string='Ngày duyệt', readonly=True)
    approved_by = fields.Many2one('res.users', string='Người duyệt', readonly=True)

    # Sender information
    sender_address_id = fields.Many2one('sender.address', string='Địa chỉ gửi', required=True, index=True)
    sender_name = fields.Char(string='Tên người gửi', related='sender_address_id.name', readonly=True, store=True)
    sender_phone = fields.Char(string='Điện thoại người gửi', related='sender_address_id.phone', readonly=True)

    # Receiver information
    receiver_name = fields.Char(string='Tên người nhận', required=True)
    receiver_phone = fields.Char(string='Điện thoại người nhận', required=True)
    receiver_street = fields.Char(string='Đường')
    receiver_city = fields.Char(string='Thành phố', required=True)
    receiver_state = fields.Char(string='Tỉnh/Thành')
    receiver_zip = fields.Char(string='Mã bưu điện')
    
    # Time slot for delivery
    time_slot = fields.Selection([
        ('morning', '6h - 12h'),
        ('afternoon', '12h - 18h'),
        ('evening', '18h - 21h'),
        ('anytime', 'Cả ngày'),
    ], string='Khung giờ nhận hàng', default='anytime')
    
    # Shipment items (one2many)
    shipment_item_ids = fields.One2many('shipment.item', 'order_id', string='Hàng hóa')
    
    # Shipment details
    total_weight = fields.Float(string='Tổng trọng lượng (kg)', compute='_compute_totals')
    total_value = fields.Float(string='Giá trị hàng hóa (VND)', compute='_compute_totals')
    item_count = fields.Integer(string='Số lượng loại hàng', compute='_compute_totals')
    
    allow_view = fields.Boolean(string='Cho phép khách xem hàng', default=True)
    reference_code = fields.Char(string='Mã tham chiếu')
    note = fields.Text(string='Ghi chú hàng hóa')
    
    # Shipping service
    shipping_service_id = fields.Many2one('shipping.service', string='Dịch vụ vận chuyển', required=True)
    shipping_cost = fields.Float(string='Cước phí (VND)', compute='_compute_shipping_cost')
    
    # Fee and payment
    currency_id = fields.Many2one('res.currency', string='Tiền tệ', 
                                   default=lambda self: self.env.company.currency_id)
    is_receiver_pay = fields.Boolean(string='Người nhận trả cước', default=False)
    cod_amount = fields.Float(string='Tiền thu hộ (COD)')
    total_fee = fields.Float(string='Tổng cước phí (VND)', compute='_compute_total_fee')
    
    pickup_at_office = fields.Boolean(string='Tới văn phòng gửi', default=False)
    order_notes = fields.Text(string='Ghi chú đơn hàng')
    
    # State log
    state_log_ids = fields.One2many('shipping.order.state.log', 'order_id', string='Lịch sử trạng thái')
    
    # Computed fields for readonly states
    is_draft = fields.Boolean(compute='_compute_state_flags', store=False)
    is_waiting_pickup = fields.Boolean(compute='_compute_state_flags', store=False)
    is_pending_return = fields.Boolean(compute='_compute_state_flags', store=False)
    can_cancel = fields.Boolean(compute='_compute_state_flags', store=False)
    can_edit = fields.Boolean(compute='_compute_state_flags', store=False)

    @api.depends('state')
    def _compute_state_flags(self):
        """Compute flags for UI control"""
        for order in self:
            order.is_draft = order.state == 'draft'
            order.is_waiting_pickup = order.state == 'waiting_pickup'
            order.is_pending_return = order.state == 'pending_return_approval'
            order.can_cancel = order.state in ['draft', 'waiting_pickup']
            order.can_edit = order.state == 'draft'

    @api.model_create_multi
    def create(self, vals_list):
        """Auto-generate order number"""
        for vals in vals_list:
            if not vals.get('order_number'):
                vals['order_number'] = self.env['ir.sequence'].next_by_code('shipping.order') or 'NEW'
        return super().create(vals_list)

    @api.depends('shipment_item_ids')
    def _compute_totals(self):
        for order in self:
            order.total_weight = sum(item.weight for item in order.shipment_item_ids)
            order.total_value = sum(item.value for item in order.shipment_item_ids)
            order.item_count = len(order.shipment_item_ids)

    @api.depends('shipping_service_id', 'total_weight')
    def _compute_shipping_cost(self):
        for order in self:
            if order.shipping_service_id:
                # Simple calculation: base price + weight surcharge (example: 5k per kg)
                weight_surcharge = order.total_weight * 5000 if order.total_weight > 0 else 0
                order.shipping_cost = order.shipping_service_id.base_price + weight_surcharge
            else:
                order.shipping_cost = 0

    @api.depends('shipping_cost', 'cod_amount', 'is_receiver_pay')
    def _compute_total_fee(self):
        for order in self:
            fee = order.shipping_cost
            if order.is_receiver_pay:
                # If receiver pays, add any additional surcharge (e.g., collection fee)
                fee += order.cod_amount * 0.01 if order.cod_amount > 0 else 0  # 1% collection fee
            order.total_fee = fee

    def _log_state_change(self, old_state, new_state):
        """Create state change log"""
        self.ensure_one()
        self.env['shipping.order.state.log'].create({
            'order_id': self.id,
            'user_id': self.env.user.id,
            'old_state': old_state,
            'new_state': new_state,
            'change_date': fields.Datetime.now(),
        })

    def write(self, vals):
        """Override write to log state changes"""
        for order in self:
            if 'state' in vals and vals['state'] != order.state:
                old_state = order.state
                result = super(ShippingOrder, order).write(vals)
                order._log_state_change(old_state, vals['state'])
                return result
        return super().write(vals)

    def action_approve(self):
        """Duyệt đơn: draft -> waiting_pickup
        Chỉ đơn nháp mới được duyệt
        Sau khi duyệt, không được chỉnh sửa nội dung
        """
        for order in self:
            if order.state != 'draft':
                raise UserError(_('Chỉ đơn nháp mới có thể được duyệt!'))
            
            # Validate required fields
            if not order.shipment_item_ids:
                raise UserError(_('Vui lòng thêm hàng hóa trước khi duyệt đơn!'))
            
            order.write({
                'state': 'waiting_pickup',
                'approved_date': fields.Datetime.now(),
                'approved_by': self.env.user.id,
            })
        return True

    def action_cancel(self):
        """Hủy đơn: chỉ được thực hiện ở trạng thái draft hoặc waiting_pickup"""
        for order in self:
            if order.state not in ['draft', 'waiting_pickup']:
                raise UserError(_('Chỉ có thể hủy đơn ở trạng thái "Đơn nháp" hoặc "Chờ lấy hàng"!'))
            
            order.write({'state': 'cancelled'})
        return True

    def action_approve_return(self):
        """Duyệt hoàn: pending_return_approval -> returned
        Đơn sẽ được trả về cho người gửi
        """
        for order in self:
            if order.state != 'pending_return_approval':
                raise UserError(_('Chỉ đơn đang "Chờ duyệt hoàn" mới có thể duyệt hoàn!'))
            
            order.write({'state': 'returned'})
        return True

    def action_redeliver(self):
        """Phát tiếp: pending_return_approval -> in_transit
        Yêu cầu giao lại cho người nhận
        """
        for order in self:
            if order.state != 'pending_return_approval':
                raise UserError(_('Chỉ đơn đang "Chờ duyệt hoàn" mới có thể yêu cầu phát lại!'))
            
            order.write({'state': 'in_transit'})
        return True

    def action_set_in_transit(self):
        """Set order to in transit (FUTA picked up)"""
        for order in self:
            if order.state != 'waiting_pickup':
                raise UserError(_('Chỉ đơn "Chờ lấy hàng" mới có thể chuyển sang vận chuyển!'))
            
            order.write({'state': 'in_transit'})
        return True

    def action_set_delivered(self):
        """Set order to delivered"""
        for order in self:
            if order.state != 'in_transit':
                raise UserError(_('Chỉ đơn "Đang vận chuyển" mới có thể chuyển sang đã giao!'))
            
            order.write({'state': 'delivered'})
        return True

    def action_request_return_approval(self):
        """Request return approval (delivery failed)"""
        for order in self:
            if order.state != 'in_transit':
                raise UserError(_('Chỉ đơn "Đang vận chuyển" mới có thể yêu cầu duyệt hoàn!'))
            
            order.write({'state': 'pending_return_approval'})
        return True

    def action_print_order(self):
        """Print shipping order"""
        return self.env.ref('hdi_shipping.action_report_shipping_order').report_action(self)

    def action_submit(self):
        """Submit order to shipping system (deprecated, use action_approve)"""
        return self.action_approve()

    def action_cancel_deprecated(self):
        """Cancel shipping order (deprecated method)"""
        return self.action_cancel()
