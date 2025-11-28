import logging

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


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

    def read(self, fields=None, load=False):
        """Safe read wrapper: if a related/computed Many2one returns the
        internal `_unknown` sentinel during web reads, Odoo's core will
        raise AttributeError when trying to access `.id`. To avoid RPC
        crashes in the web client we catch exceptions and return a
        per-field safe result (False for failing fields) and log the
        problematic field names for debugging.
        """
        try:
            return super().read(fields=fields, load=load)
        except Exception as exc:
            _logger.exception('barcode.item: read() fallback triggered: %s', exc)
            field_names = fields or list(self._fields.keys())
            results = []
            for rec in self:
                row = {}
                # Ensure `id` is always present (web client expects it)
                row['id'] = rec.id or False
                for name in field_names:
                    try:
                        field = self._fields.get(name)
                        val = rec[name]
                        # Convert relational recordsets to primitive types
                        if field and field.type == 'many2one':
                            row[name] = val.id or False
                        elif field and field.type in ('one2many', 'many2many'):
                            row[name] = val.ids
                        else:
                            # For other field types, use the raw value
                            # (will be a basic Python type or False)
                            row[name] = val
                    except Exception as fexc:
                        _logger.warning(
                            "barcode.item read: field '%s' failed for record %s: %s",
                            name, getattr(rec, 'id', repr(rec)), fexc
                        )
                        row[name] = False
                results.append(row)
            return results
