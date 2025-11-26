from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Thuộc tính Moving (A/B/C/E)
    moving_type = fields.Selection([
        ('a', 'A - High Moving'),
        ('b', 'B - Medium Moving'),
        ('c', 'C - Low Moving'),
        ('e', 'E - Extra Slow Moving'),
    ], string='Moving Type', default='b',
       help='Classification based on product turnover rate')
    
    # Số lượng tiêu chuẩn trong 1 batch
    standard_batch_qty = fields.Float(
        string='Standard Batch Quantity',
        default=1.0,
        help='Standard quantity per batch for this product'
    )
    
    # Thể tích sản phẩm (đã có sẵn trong Odoo: volume)
    # Nhưng thêm computed field để dễ sử dụng
    product_volume = fields.Float(
        related='volume',
        string='Product Volume (m³)',
        readonly=True
    )
    
    # Preferred locations for this product
    preferred_location_ids = fields.Many2many(
        'stock.location',
        'product_location_preferred_rel',
        'product_id',
        'location_id',
        string='Preferred Locations',
        domain=[('usage', '=', 'internal')]
    )


class ProductProduct(models.Model):
    _inherit = 'product.product'

    moving_type = fields.Selection(
        related='product_tmpl_id.moving_type',
        store=True,
        readonly=False
    )
    standard_batch_qty = fields.Float(
        related='product_tmpl_id.standard_batch_qty',
        store=True,
        readonly=False
    )
