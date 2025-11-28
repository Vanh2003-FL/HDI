from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class BarcodeItem(models.Model):
    """
    Model quản lý hàng lẻ không thuộc batch nào
    Dùng cho luồng NK_NV_01 (B) - Hàng lẻ không batch
    """
    _inherit = 'barcode.item'
    _description = 'Hàng lẻ mã vạch (mở rộng WMS)'
    _order = 'create_date desc'

    # Additional fields/extensions provided by WMS module
    quantity = fields.Float(
        string='Số lượng',
        default=1.0,
        digits='Product Unit of Measure',
        tracking=True
    )
    location_confirmed = fields.Boolean(
        string='Đã xác nhận vị trí',
        default=False,
        help='Đã xác nhận vị trí đặt hàng'
    )
    receipt_type = fields.Selection([
        ('production_domestic', 'NK_NV_01: Sản xuất nội địa'),
        ('production_export', 'NK_NV_02: Sản xuất xuất khẩu'),
        ('import', 'NK_NV_03: Nhập khẩu'),
        ('transfer_return', 'NK_NV_04: Chuyển kho/Trả lại'),
    ], string='Loại nhập kho')
    lot_id = fields.Many2one(
        'stock.lot',
        string='Lot/Serial',
        help='Nếu có Lot/Serial'
    )

    @api.constrains('quantity')
    def _check_quantity(self):
        for item in self:
            if item.quantity <= 0:
                raise ValidationError(_('Số lượng phải lớn hơn 0.'))

    def action_place(self):
        """Xác nhận đã đặt vào vị trí"""
        if not self.location_id:
            raise ValidationError(_('Vui lòng chọn vị trí trước.'))
        self.write({
            'state': 'placed',
            'location_confirmed': True
        })

    # Note: removed uom_id computed field to avoid _unknown sentinel issues in UI

    def action_reset(self):
        """Reset về draft"""
        self.write({
            'state': 'draft',
            'location_confirmed': False
        })

    @api.model
    def scan_barcode(self, barcode, product_id=None, quantity=1.0):
        """API để quét barcode từ thiết bị
        Returns: barcode.item record hoặc error
        """
        item = self.search([('name', '=', barcode)], limit=1)
        if item:
            return {
                'success': True,
                'item': item,
                'message': 'Mã vạch đã tồn tại'
            }
        if not product_id:
            return {
                'success': False,
                'message': 'Cần Product ID để tạo mã vạch mới'
            }
        item = self.create({
            'name': barcode,
            'product_id': product_id,
            'quantity': quantity,
            'state': 'scanned'
        })
        return {
            'success': True,
            'item': item,
            'message': 'Tạo mã vạch mới thành công'
        }


class BarcodeItemList(models.Model):
    """
    Bảng kê hàng lẻ - Picking List for barcode items
    """
    _name = 'barcode.item.list'
    _description = 'Bảng kê hàng lẻ'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Mã bảng kê',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    date = fields.Datetime(
        string='Ngày',
        default=fields.Datetime.now,
        required=True
    )
    item_ids = fields.Many2many(
        'barcode.item',
        string='Hàng lẻ mã vạch'
    )
    item_count = fields.Integer(
        compute='_compute_item_count',
        string='Tổng số hàng'
    )
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('confirmed', 'Đã xác nhận'),
        ('done', 'Hoàn thành'),
    ], default='draft', tracking=True)
    
    notes = fields.Text(string='Ghi chú')
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company
    )

    @api.depends('item_ids')
    def _compute_item_count(self):
        for record in self:
            record.item_count = len(record.item_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('barcode.item.list') or _('New')
        return super().create(vals_list)

    def action_confirm(self):
        self.state = 'confirmed'

    def action_done(self):
        # Confirm all items
        self.item_ids.filtered(lambda i: i.state != 'confirmed').action_confirm()
        self.state = 'done'
