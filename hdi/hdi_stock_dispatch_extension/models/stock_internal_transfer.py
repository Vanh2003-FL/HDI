from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class StockInternalTransfer(models.Model):
    """Phiếu điều chuyển nội bộ - ĐC_NV_01"""
    _name = 'stock.internal.transfer'
    _description = 'Internal Transfer'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Transfer Reference',
        required=True,
        readonly=True,
        default=lambda self: _('New')
    )
    
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True
    )
    
    # Source & Destination
    location_src_id = fields.Many2one(
        'stock.location',
        string='Source Location',
        required=True,
        domain=[('usage', '=', 'internal')]
    )
    location_dest_id = fields.Many2one(
        'stock.location',
        string='Destination Location',
        required=True,
        domain=[('usage', '=', 'internal')]
    )
    suggested_location_id = fields.Many2one(
        'stock.location',
        string='Suggested Destination',
        help='AI-suggested destination location'
    )
    
    # Batch or Barcode
    transfer_type = fields.Selection([
        ('batch', 'Transfer Batch'),
        ('barcode', 'Transfer Barcode Items'),
    ], string='Transfer Type', required=True, default='batch')
    
    lot_id = fields.Many2one(
        'stock.lot',
        string='Batch/Lot',
        domain="[('product_id', '=', product_id)]"
    )
    barcode_item_ids = fields.Many2many(
        'barcode.item',
        string='Barcode Items'
    )
    
    quantity = fields.Float(
        string='Quantity',
        required=True,
        digits='Product Unit of Measure'
    )
    
    # Assignment
    assigned_user_id = fields.Many2one(
        'res.users',
        string='Assigned To',
        tracking=True
    )
    
    # State: draft → waiting → in_progress → done → approved
    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting', 'Waiting'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('approved', 'Approved'),
        ('cancel', 'Cancelled')
    ], string='Status', default='draft', tracking=True)
    
    # Verification
    stock_verified = fields.Boolean(
        string='Stock Verified',
        help='Nhân viên xác nhận có hàng tại vị trí'
    )
    
    transfer_date = fields.Datetime(
        string='Transfer Date',
        default=fields.Datetime.now
    )
    completion_date = fields.Datetime(
        string='Completion Date'
    )
    
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('stock.internal.transfer') or _('New')
        return super().create(vals_list)

    @api.onchange('product_id', 'location_src_id')
    def _onchange_suggest_destination(self):
        """Gợi ý vị trí đích dựa vào putaway engine"""
        if self.product_id:
            suggestion = self.env['putaway.suggestion'].get_suggested_location(
                product_id=self.product_id.id,
                quantity=self.quantity or 0
            )
            if suggestion:
                self.suggested_location_id = suggestion.id

    def action_assign(self):
        """Gán nhân viên và chuyển sang waiting"""
        self.ensure_one()
        if not self.assigned_user_id:
            self.assigned_user_id = self.env.user.id
        self.state = 'waiting'

    def action_start(self):
        """Nhân viên bắt đầu thực hiện"""
        self.ensure_one()
        self.state = 'in_progress'

    def action_verify_stock(self):
        """Xác nhận có hàng tại vị trí"""
        self.ensure_one()
        self.stock_verified = True

    def action_complete(self):
        """Nhân viên hoàn thành"""
        self.ensure_one()
        if not self.stock_verified:
            raise UserError(_('Please verify stock availability first.'))
        
        self.write({
            'state': 'done',
            'completion_date': fields.Datetime.now(),
        })

    def action_approve(self):
        """Quản lý kho approve"""
        self.ensure_one()
        if self.state != 'done':
            raise UserError(_('Transfer must be completed before approval.'))
        
        # Create stock move
        self.env['stock.move'].create({
            'name': self.name,
            'product_id': self.product_id.id,
            'product_uom_qty': self.quantity,
            'product_uom': self.product_id.uom_id.id,
            'location_id': self.location_src_id.id,
            'location_dest_id': self.location_dest_id.id,
            'state': 'done',
        })
        
        self.state = 'approved'

    def action_cancel(self):
        self.ensure_one()
        if self.state == 'approved':
            raise UserError(_('Cannot cancel approved transfer.'))
        self.state = 'cancel'
