from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class ReceiptOperation(models.Model):
    """
    Model tổng hợp cho 4 luồng nhập kho: NK_NV_01 đến NK_NV_04
    """
    _name = 'receipt.operation'
    _description = 'Receipt Operation - Nhập kho'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    
    # Receipt Type
    receipt_type = fields.Selection([
        ('production_domestic', 'NK_NV_01: Sản xuất nội địa'),
        ('production_export', 'NK_NV_02: Sản xuất xuất khẩu'),
        ('import', 'NK_NV_03: Nhập khẩu'),
        ('transfer_return', 'NK_NV_04: Chuyển kho/Trả lại'),
    ], string='Receipt Type', required=True, tracking=True)
    
    date = fields.Datetime(
        string='Receipt Date',
        default=fields.Datetime.now,
        required=True
    )
    
    # State: new → done → approved → transferred
    state = fields.Selection([
        ('new', 'New'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('approved', 'Approved by Warehouse Manager'),
        ('transferred', 'Transferred/Handover Complete'),
        ('cancel', 'Cancelled')
    ], string='Status', default='new', tracking=True)
    
    # Batch management
    batch_ids = fields.Many2many(
        'stock.lot',
        'receipt_batch_rel',
        'receipt_id',
        'batch_id',
        string='Batches',
        domain="[('is_batch', '=', True)]"
    )
    batch_count = fields.Integer(
        compute='_compute_batch_count',
        string='Batch Count'
    )
    
    # Barcode Items (hàng lẻ không batch)
    barcode_list_ids = fields.Many2many(
        'barcode.item.list',
        string='Bảng kê hàng lẻ'
    )
    barcode_item_count = fields.Integer(
        compute='_compute_barcode_count',
        string='Barcode Items'
    )
    
    # Related Receipt Extension
    stock_receipt_id = fields.Many2one(
        'stock.receipt',
        string='Stock Receipt',
        help='Link to detailed receipt information'
    )
    picking_id = fields.Many2one(
        'stock.picking',
        string='Stock Picking'
    )
    
    # Warehouse
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
        required=True,
        default=lambda self: self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
    )
    
    # Assignee
    warehouse_manager_id = fields.Many2one(
        'res.users',
        string='Warehouse Manager',
        help='Quản lý kho phê duyệt'
    )
    production_manager_id = fields.Many2one(
        'res.users',
        string='Production Manager',
        help='Quản lý sản xuất bàn giao (cho NK_NV_01, NK_NV_02)'
    )
    
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company
    )

    @api.depends('batch_ids')
    def _compute_batch_count(self):
        for record in self:
            record.batch_count = len(record.batch_ids)

    @api.depends('barcode_list_ids')
    def _compute_barcode_count(self):
        for record in self:
            total = sum(record.barcode_list_ids.mapped('item_count'))
            record.barcode_item_count = total

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                receipt_type = vals.get('receipt_type', 'production_domestic')
                prefix_map = {
                    'production_domestic': 'NK01',
                    'production_export': 'NK02',
                    'import': 'NK03',
                    'transfer_return': 'NK04',
                }
                prefix = prefix_map.get(receipt_type, 'RCP')
                vals['name'] = self.env['ir.sequence'].next_by_code('receipt.operation') or f'{prefix}/New'
        return super().create(vals_list)

    def action_start_process(self):
        """Bắt đầu xử lý nhập kho"""
        self.state = 'in_progress'

    def action_done(self):
        """Hoàn thành phiếu nhập"""
        self.ensure_one()
        
        # Validation
        if not self.batch_ids and not self.barcode_list_ids:
            raise UserError(_('Must have at least one batch or barcode item list.'))
        
        # Check all batches are confirmed
        unconfirmed_batches = self.batch_ids.filtered(lambda b: b.batch_state != 'confirmed')
        if unconfirmed_batches:
            raise UserError(_(f'{len(unconfirmed_batches)} batches are not confirmed yet.'))
        
        self.state = 'done'

    def action_approve(self):
        """Quản lý kho xác nhận"""
        self.ensure_one()
        
        if self.state != 'done':
            raise UserError(_('Receipt must be done before approval.'))
        
        self.write({
            'state': 'approved',
            'warehouse_manager_id': self.env.user.id
        })

    def action_transfer(self):
        """Quản lý sản xuất bàn giao → Kết thúc"""
        self.ensure_one()
        
        if self.state != 'approved':
            raise UserError(_('Receipt must be approved before transfer.'))
        
        if self.receipt_type in ['production_domestic', 'production_export']:
            if not self.production_manager_id:
                self.production_manager_id = self.env.user.id
        
        self.state = 'transferred'

    def action_cancel(self):
        """Cancel phiếu nhập"""
        self.state = 'cancel'

    def action_view_batches(self):
        """View batches"""
        return {
            'name': _('Batches'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.lot',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.batch_ids.ids)],
            'context': {'default_receipt_type': self.receipt_type}
        }

    def action_create_batch(self):
        """Tạo batch mới cho phiếu nhập"""
        return {
            'name': _('Create Batch'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.lot',
            'view_mode': 'form',
            'view_id': self.env.ref('hdi_wms_operation.view_stock_lot_batch_form').id,
            'context': {
                'default_is_batch': True,
                'default_receipt_type': self.receipt_type,
                'default_company_id': self.company_id.id,
            },
            'target': 'new'
        }

    def action_create_barcode_list(self):
        """Tạo bảng kê hàng lẻ"""
        return {
            'name': _('Create Barcode List'),
            'type': 'ir.actions.act_window',
            'res_model': 'barcode.item.list',
            'view_mode': 'form',
            'target': 'new'
        }
