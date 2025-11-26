from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class TransferOperation(models.Model):
    """
    ĐC_NV_01: Điều chuyển vị trí trong kho
    State: draft → waiting → in_progress → done → approved
    """
    _name = 'transfer.operation'
    _description = 'Transfer Operation - Điều chuyển'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    date = fields.Datetime(
        string='Transfer Date',
        default=fields.Datetime.now,
        required=True
    )
    
    # State machine
    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting', 'Waiting for Worker'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('approved', 'Approved'),
        ('cancel', 'Cancelled')
    ], string='Status', default='draft', tracking=True)
    
    # Transfer lines
    line_ids = fields.One2many(
        'transfer.operation.line',
        'transfer_id',
        string='Transfer Lines'
    )
    
    # Assignment
    assigned_user_id = fields.Many2one(
        'res.users',
        string='Assigned Worker',
        tracking=True
    )
    manager_id = fields.Many2one(
        'res.users',
        string='Warehouse Manager'
    )
    
    # Statistics
    total_lines = fields.Integer(
        compute='_compute_statistics',
        string='Total Lines'
    )
    completed_lines = fields.Integer(
        compute='_compute_statistics',
        string='Completed Lines'
    )
    
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
        required=True
    )
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company
    )

    @api.depends('line_ids', 'line_ids.state')
    def _compute_statistics(self):
        for record in self:
            record.total_lines = len(record.line_ids)
            record.completed_lines = len(record.line_ids.filtered(lambda l: l.state == 'done'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('transfer.operation') or 'DC/New'
        return super().create(vals_list)

    def action_assign(self):
        """Gán nhân viên và chuyển sang waiting"""
        self.ensure_one()
        if not self.assigned_user_id:
            self.assigned_user_id = self.env.user.id
        self.state = 'waiting'

    def action_start(self):
        """Nhân viên bắt đầu thực hiện"""
        self.state = 'in_progress'

    def action_done(self):
        """Nhân viên xác nhận hoàn thành"""
        if any(line.state != 'done' for line in self.line_ids):
            raise UserError(_('All lines must be completed.'))
        self.state = 'done'

    def action_approve(self):
        """Quản lý kho approve"""
        self.write({
            'state': 'approved',
            'manager_id': self.env.user.id
        })

    def action_cancel(self):
        self.state = 'cancel'


class TransferOperationLine(models.Model):
    _name = 'transfer.operation.line'
    _description = 'Transfer Operation Line'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    transfer_id = fields.Many2one(
        'transfer.operation',
        required=True,
        ondelete='cascade'
    )
    
    # Product & Batch
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True
    )
    batch_id = fields.Many2one(
        'stock.lot',
        string='Batch',
        domain="[('product_id', '=', product_id), ('is_batch', '=', True)]"
    )
    barcode_item_id = fields.Many2one(
        'barcode.item',
        string='Barcode Item'
    )
    quantity = fields.Float(
        string='Quantity',
        digits='Product Unit of Measure',
        required=True
    )
    
    # Locations
    source_location_id = fields.Many2one(
        'stock.location',
        string='From Location',
        required=True
    )
    suggested_dest_location_id = fields.Many2one(
        'stock.location',
        string='Suggested To Location',
        help='Vị trí được gợi ý'
    )
    dest_location_id = fields.Many2one(
        'stock.location',
        string='To Location',
        required=True
    )
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed at Source'),
        ('in_transit', 'In Transit'),
        ('done', 'Done'),
    ], default='draft')
    
    stock_available = fields.Boolean(
        string='Stock Available',
        help='Xác nhận có hàng tại vị trí nguồn'
    )
    
    notes = fields.Char(string='Notes')

    @api.onchange('product_id', 'quantity')
    def _onchange_suggest_location(self):
        """Auto suggest destination location"""
        if self.product_id and self.quantity:
            suggestion = self.env['putaway.suggestion'].get_suggested_location(
                product_id=self.product_id.id,
                quantity=self.quantity
            )
            if suggestion:
                self.suggested_dest_location_id = suggestion.id
                if not self.dest_location_id:
                    self.dest_location_id = suggestion.id

    def action_confirm_source(self):
        """Nhân viên xác nhận có hàng tại nguồn"""
        self.write({
            'stock_available': True,
            'state': 'confirmed'
        })

    def action_in_transit(self):
        """Đang di chuyển"""
        self.state = 'in_transit'

    def action_done(self):
        """Hoàn thành chuyển"""
        self.state = 'done'
