from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Master Data theo tài liệu
    standard_batch_qty = fields.Float(
        string='Số lượng chuẩn trong 1 Batch',
        help='Số lượng tiêu chuẩn của sản phẩm trong một batch'
    )
    moving_classification = fields.Selection([
        ('a', 'A - Fast Moving'),
        ('b', 'B - Medium Moving'),
        ('c', 'C - Slow Moving'),
        ('e', 'E - Extra Slow Moving'),
    ], string='Moving Classification',
       help='Phân loại tốc độ luân chuyển sản phẩm')
    
    # Priority locations
    priority_location_ids = fields.Many2many(
        'stock.location',
        'product_location_priority_rel',
        'product_id',
        'location_id',
        string='Priority Locations',
        help='Vị trí ưu tiên để đặt sản phẩm này'
    )
    
    # Batch management
    require_batch = fields.Boolean(
        string='Yêu cầu Batch',
        default=True,
        help='Sản phẩm này có yêu cầu quản lý theo batch không'
    )
    batch_prefix = fields.Char(
        string='Batch Prefix',
        help='Tiền tố cho mã batch (vd: BAT-)'
    )
    
    # Quality Control
    requires_qc = fields.Boolean(
        string='Requires QC',
        default=False,
        help='Sản phẩm cần kiểm tra chất lượng'
    )
    qc_days = fields.Integer(
        string='QC Days',
        default=0,
        help='Số ngày cần để kiểm tra chất lượng'
    )
    
    # FIFO Settings
    enforce_fifo = fields.Boolean(
        string='Enforce FIFO',
        default=False,
        help='Bắt buộc xuất kho theo FIFO (First In First Out)'
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
