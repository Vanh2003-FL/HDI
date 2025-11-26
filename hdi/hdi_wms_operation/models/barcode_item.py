from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class BarcodeItem(models.Model):
    """
    Model quản lý hàng lẻ không thuộc batch nào
    Dùng cho luồng NK_NV_01 (B) - Hàng lẻ không batch
    """
    _name = 'barcode.item'
    _description = 'Barcode Item - Hàng lẻ'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Barcode',
        required=True,
        index=True,
        tracking=True
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        tracking=True
    )
    quantity = fields.Float(
        string='Quantity',
        default=1.0,
        digits='Product Unit of Measure',
        tracking=True
    )
    uom_id = fields.Many2one(
        'uom.uom',
        string='UoM',
        related='product_id.uom_id',
        readonly=True
    )
    
    # Location tracking
    location_id = fields.Many2one(
        'stock.location',
        string='Current Location',
        tracking=True
    )
    location_confirmed = fields.Boolean(
        string='Location Confirmed',
        default=False,
        help='Đã xác nhận vị trí đặt hàng'
    )
    
    # State management
    state = fields.Selection([
        ('draft', 'Draft'),
        ('scanned', 'Scanned'),
        ('placed', 'Placed'),
        ('confirmed', 'Confirmed'),
    ], string='Status', default='draft', tracking=True)
    
    # Receipt information
    receipt_id = fields.Many2one(
        'stock.receipt',
        string='Receipt',
        help='Phiếu nhập liên quan'
    )
    receipt_type = fields.Selection([
        ('production_domestic', 'NK_NV_01: Sản xuất nội địa'),
        ('production_export', 'NK_NV_02: Sản xuất xuất khẩu'),
        ('import', 'NK_NV_03: Nhập khẩu'),
        ('transfer_return', 'NK_NV_04: Chuyển kho/Trả lại'),
    ], string='Receipt Type')
    
    # Additional info
    lot_id = fields.Many2one(
        'stock.lot',
        string='Lot/Serial',
        help='Nếu có lot/serial number'
    )
    notes = fields.Text(string='Notes')
    
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company
    )

    _sql_constraints = [
        ('barcode_unique', 'unique(name, company_id)', 'Barcode must be unique per company!')
    ]

    @api.constrains('quantity')
    def _check_quantity(self):
        for item in self:
            if item.quantity <= 0:
                raise ValidationError(_('Quantity must be greater than zero.'))

    def action_scan(self):
        """Xác nhận đã quét barcode"""
        self.write({'state': 'scanned'})

    def action_place(self):
        """Xác nhận đã đặt vào vị trí"""
        if not self.location_id:
            raise ValidationError(_('Please select a location first.'))
        self.write({
            'state': 'placed',
            'location_confirmed': True
        })

    def action_confirm(self):
        """Xác nhận hoàn tất"""
        if not self.location_confirmed:
            raise ValidationError(_('Please confirm location first.'))
        self.state = 'confirmed'

    def action_reset(self):
        """Reset về draft"""
        self.write({
            'state': 'draft',
            'location_confirmed': False
        })

    @api.model
    def scan_barcode(self, barcode, product_id=None, quantity=1.0):
        """
        API để quét barcode từ thiết bị
        Returns: barcode.item record hoặc error
        """
        # Check if barcode exists
        item = self.search([('name', '=', barcode)], limit=1)
        
        if item:
            # Barcode đã tồn tại
            return {
                'success': True,
                'item': item,
                'message': 'Barcode already exists'
            }
        
        if not product_id:
            return {
                'success': False,
                'message': 'Product ID required for new barcode'
            }
        
        # Create new barcode item
        item = self.create({
            'name': barcode,
            'product_id': product_id,
            'quantity': quantity,
            'state': 'scanned'
        })
        
        return {
            'success': True,
            'item': item,
            'message': 'New barcode created'
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
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    date = fields.Datetime(
        string='Date',
        default=fields.Datetime.now,
        required=True
    )
    item_ids = fields.Many2many(
        'barcode.item',
        string='Barcode Items'
    )
    item_count = fields.Integer(
        compute='_compute_item_count',
        string='Total Items'
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
    ], default='draft', tracking=True)
    
    notes = fields.Text(string='Notes')
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
