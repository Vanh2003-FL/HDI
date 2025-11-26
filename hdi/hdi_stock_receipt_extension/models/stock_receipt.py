from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class StockReceipt(models.Model):
    _name = 'stock.receipt'
    _description = 'Stock Receipt Extension'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'receipt_date desc, id desc'

    name = fields.Char(
        string='Receipt Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    picking_id = fields.Many2one(
        'stock.picking',
        string='Stock Picking',
        required=True,
        domain=[('picking_type_code', '=', 'incoming')],
        tracking=True
    )
    
    # Container Information
    container_no = fields.Char(
        string='Container Number',
        tracking=True
    )
    container_type = fields.Selection([
        ('20ft', '20 Feet'),
        ('40ft', '40 Feet'),
        ('40hc', '40 Feet High Cube'),
        ('45hc', '45 Feet High Cube'),
        ('other', 'Other'),
    ], string='Container Type')
    seal_no = fields.Char(
        string='Seal Number',
        tracking=True
    )
    
    # Customs Information
    customs_declaration_no = fields.Char(
        string='Customs Declaration (Tờ khai HQ)',
        tracking=True
    )
    customs_date = fields.Date(
        string='Customs Date'
    )
    bill_of_lading = fields.Char(
        string='Bill of Lading (B/L)',
        tracking=True
    )
    import_license = fields.Char(
        string='Import License'
    )
    
    # QC Information
    qc_required = fields.Boolean(
        string='QC Required',
        default=True
    )
    qc_status = fields.Selection([
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('passed', 'Passed'),
        ('failed', 'Failed'),
        ('partial', 'Partial Pass'),
    ], string='QC Status', default='pending', tracking=True)
    qc_date = fields.Datetime(
        string='QC Date'
    )
    qc_user_id = fields.Many2one(
        'res.users',
        string='QC Inspector'
    )
    qc_notes = fields.Text(
        string='QC Notes'
    )
    
    # Batch Lines
    batch_line_ids = fields.One2many(
        'receipt.batch.line',
        'receipt_id',
        string='Batch Lines'
    )
    
    # Receipt Details
    receipt_date = fields.Datetime(
        string='Receipt Date',
        default=fields.Datetime.now,
        required=True,
        tracking=True
    )
    vehicle_no = fields.Char(
        string='Vehicle Number'
    )
    driver_name = fields.Char(
        string='Driver Name'
    )
    driver_phone = fields.Char(
        string='Driver Phone'
    )
    
    # Status
    # Receipt type theo 4 luồng chính
    receipt_type = fields.Selection([
        ('production_domestic', 'NK_NV_01: Production Domestic'),
        ('production_export', 'NK_NV_02: Production Export'),
        ('import', 'NK_NV_03: Import'),
        ('transfer_return', 'NK_NV_04: Transfer/Return'),
    ], string='Receipt Type', required=True, default='production_domestic',
       tracking=True)
    
    # State theo tài liệu: new → done → approved → transferred
    state = fields.Selection([
        ('new', 'New'),
        ('draft', 'Draft'),
        ('done', 'Done'),
        ('approved', 'Approved'),
        ('transferred', 'Transferred'),
        ('cancel', 'Cancelled')
    ], string='Status', default='new', tracking=True)
    
    # Work Order cho xuất khẩu (NK_NV_02)
    work_order_export = fields.Char(
        string='Export Work Order',
        help='Required for NK_NV_02'
    )
    
    # Số chứng từ SAP (NK_NV_03)
    sap_document_no = fields.Char(
        string='SAP Document Number',
        help='Required for NK_NV_03'
    )
    
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        related='picking_id.picking_type_id.warehouse_id',
        string='Warehouse',
        store=True,
        readonly=True
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('stock.receipt') or _('New')
        return super().create(vals_list)

    def action_start_qc(self):
        self.ensure_one()
        if not self.qc_required:
            raise UserError(_('QC is not required for this receipt.'))
        self.write({
            'state': 'qc',
            'qc_status': 'in_progress',
            'qc_date': fields.Datetime.now(),
            'qc_user_id': self.env.user.id,
        })

    def action_qc_pass(self):
        self.ensure_one()
        self.write({
            'state': 'approved',
            'qc_status': 'passed',
        })

    def action_qc_fail(self):
        self.ensure_one()
        self.write({
            'qc_status': 'failed',
        })

    def action_done(self):
        self.ensure_one()
        if self.qc_required and self.qc_status not in ['passed', 'partial']:
            raise UserError(_('QC must be completed before marking as done.'))
        self.state = 'done'

    def action_cancel(self):
        self.ensure_one()
        if self.state == 'done':
            raise UserError(_('Cannot cancel a completed receipt.'))
        self.state = 'cancel'

    def action_draft(self):
        self.ensure_one()
        self.state = 'draft'
