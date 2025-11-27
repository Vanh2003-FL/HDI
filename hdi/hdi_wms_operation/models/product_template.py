from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Master Data theo tài liệu
    standard_batch_qty = fields.Float(
        string='Số lượng chuẩn trong 1 Batch',
        help='Số lượng tiêu chuẩn của sản phẩm trong một batch'
    )
    moving_classification = fields.Selection([
        ('a', 'A - Luân chuyển nhanh'),
        ('b', 'B - Luân chuyển trung bình'),
        ('c', 'C - Luân chuyển chậm'),
        ('e', 'E - Luân chuyển rất chậm'),
    ], string='Phân loại luân chuyển',
       help='Phân loại tốc độ luân chuyển sản phẩm theo ABC')
    
    # Priority locations
    priority_location_ids = fields.Many2many(
        'stock.location',
        'product_location_priority_rel',
        'product_id',
        'location_id',
        string='Vị trí ưu tiên',
        help='Các vị trí kho ưu tiên để đặt sản phẩm này'
    )
    
    # Batch management
    require_batch = fields.Boolean(
        string='Yêu cầu quản lý batch',
        default=True,
        help='Sản phẩm này có yêu cầu quản lý theo batch không'
    )
    batch_prefix = fields.Char(
        string='Tiền tố batch',
        help='Tiền tố cho mã batch (ví dụ: BAT-)'
    )
    
    # Quality Control
    requires_qc = fields.Boolean(
        string='Yêu cầu kiểm tra chất lượng',
        default=False,
        help='Sản phẩm này cần kiểm tra chất lượng trước khi xuất kho'
    )
    qc_days = fields.Integer(
        string='Số ngày kiểm tra chất lượng',
        default=0,
        help='Số ngày cần để kiểm tra chất lượng sản phẩm'
    )
    
    # FIFO Settings
    enforce_fifo = fields.Boolean(
        string='Bắt buộc xuất kho theo FIFO',
        default=False,
        help='Bắt buộc xuất kho theo nguyên tắc FIFO (Nhập trước xuất trước)'
    )


class ProductProduct(models.Model):
    _inherit = 'product.product'

    standard_batch_qty = fields.Float(
        related='product_tmpl_id.standard_batch_qty',
        readonly=False,
        store=True
    )
    moving_classification = fields.Selection(
        related='product_tmpl_id.moving_classification',
        readonly=False,
        store=True
    )
    require_batch = fields.Boolean(
        related='product_tmpl_id.require_batch',
        readonly=False,
        store=True
    )
