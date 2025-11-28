from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class BarcodeItem(models.Model):
    """Hàng lẻ không có Batch - quản lý từng mã vạch riêng lẻ"""
    _name = 'barcode.item'
    _description = 'Hàng lẻ mã vạch (không theo batch)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Mã vạch',
        required=True,
        index=True,
        help='Mã vạch sản phẩm (mã duy nhất cho hàng lẻ)'
    )
    product_id = fields.Many2one(
        'product.product',
        string='Sản phẩm',
        required=True,
        index=True
    )
    location_id = fields.Many2one(
        'stock.location',
        string='Vị trí hiện tại',
        required=True,
        domain=[('usage', '=', 'internal')]
    )
    
    # Status
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('scanned', 'Đã quét'),
        ('placed', 'Đã đặt'),
        ('confirmed', 'Đã xác nhận'),
        ('out', 'Hết hàng'),
    ], string='Trạng thái', default='draft', tracking=True)
    
    # Receipt information
    receipt_id = fields.Many2one(
        'stock.receipt',
        string='Phiếu nhập liên quan'
    )
    receipt_date = fields.Datetime(
        string='Ngày nhập',
        default=fields.Datetime.now
    )
    
    # Picking information (for outbound)
    picking_id = fields.Many2one(
        'stock.picking',
        string='Phiếu xuất liên quan'
    )
    picked_date = fields.Datetime(
        string='Ngày lấy'
    )
    
    # Additional info
    notes = fields.Text(string='Ghi chú')
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company
    )

    _sql_constraints = [
        ('barcode_unique', 'unique(name, company_id)',
         'Mã vạch phải là duy nhất trong công ty!')
    ]

    @api.constrains('name')
    def _check_barcode(self):
        for item in self:
            if not item.name:
                raise ValidationError(_('Mã vạch không được để trống.'))

    def action_scan(self):
        """Gắn trạng thái 'Đã quét' khi quét mã vạch"""
        self.ensure_one()
        self.state = 'scanned'

    def action_place(self, location_id):
        """Ghi nhận vị trí đặt hàng và chuyển trạng thái sang 'Đã đặt'"""
        self.ensure_one()
        self.write({
            'location_id': location_id,
            'state': 'placed',
        })

    def action_confirm(self):
        """Xác nhận hoàn tất xử lý hàng lẻ"""
        self.ensure_one()
        self.state = 'confirmed'

    def action_pick(self, picking_id):
        """Đánh dấu đã lấy hàng cho xuất kho"""
        self.ensure_one()
        self.write({
            'picking_id': picking_id,
            'picked_date': fields.Datetime.now(),
            'state': 'out',
        })
