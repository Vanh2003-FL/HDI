# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class HdiBatch(models.Model):
    _name = 'hdi.batch'
    _description = 'Batch / LPN / Pallet'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'barcodes.barcode_events_mixin']
    _order = 'create_date desc, id desc'

    # ===== BASIC INFO =====
    name = fields.Char(
        string='Batch Number',
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: _('New'),
        tracking=True,
    )

    barcode = fields.Char(
        string='Barcode/LPN',
        copy=False,
        index=True,
        tracking=True,
        help="Barcode or License Plate Number for scanning"
    )

    batch_type = fields.Selection([
        ('pallet', 'Pallet'),
        ('lpn', 'LPN'),
        ('container', 'Container'),
        ('loose', 'Loose Items'),
    ], string='Batch Type', default='pallet', required=True, tracking=True)

    picking_id = fields.Many2one(
        'stock.picking',
        string='Related Picking',
        index=True,
        tracking=True,
        help="Link to core stock.picking (Incoming/Outgoing/Internal Transfer)"
    )

    move_ids = fields.One2many(
        'stock.move',
        'batch_id',
        string='Stock Moves',
        help="All stock.move linked to this batch - maintains core inventory flow"
    )

    quant_ids = fields.One2many(
        'stock.quant',
        'batch_id',
        string='Quants',
        help="Actual inventory quants in this batch - CORE inventory data"
    )

    putaway_suggestion_ids = fields.One2many(
        'hdi.putaway.suggestion',
        'batch_id',
        string='Putaway Suggestions',
        help="Location suggestions for this batch"
    )

    location_id = fields.Many2one(
        'stock.location',
        string='Current Location',
        required=True,
        index=True,
        tracking=True,
        help="Current storage location (from core stock.location)"
    )

    location_dest_id = fields.Many2one(
        'stock.location',
        string='Destination Location',
        tracking=True,
        help="Planned destination for putaway"
    )

    # ===== WMS SPECIFIC FIELDS =====
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_receiving', 'In Receiving'),
        ('in_putaway', 'In Putaway'),
        ('stored', 'Stored'),
        ('in_picking', 'In Picking'),
        ('shipped', 'Shipped'),
        ('cancel', 'Cancelled'),
    ], string='State', default='draft', required=True, tracking=True)

    wms_status = fields.Selection([
        ('empty', 'Empty'),
        ('partial', 'Partial'),
        ('full', 'Full'),
        ('mixed', 'Mixed Products'),
    ], string='WMS Status', compute='_compute_wms_status', store=True)

    # ===== PRODUCT & QUANTITY =====
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        help="Primary product (for single-product batches)"
    )

    planned_quantity = fields.Float(
        string='Planned Quantity',
        digits='Product Unit of Measure',
        help="Expected quantity (entered when creating batch, before actual receipt)"
    )

    total_quantity = fields.Float(
        string='Total Quantity',
        compute='_compute_quantities',
        store=True,
        help="Total quantity from all quants"
    )

    available_quantity = fields.Float(
        string='Available Quantity',
        compute='_compute_quantities',
        store=True,
    )

    reserved_quantity = fields.Float(
        string='Reserved Quantity',
        compute='_compute_quantities',
        store=True,
    )

    # ===== PHYSICAL ATTRIBUTES =====
    weight = fields.Float(string='Weight (kg)', digits='Stock Weight')
    volume = fields.Float(string='Volume (m³)', digits=(16, 4))
    height = fields.Float(string='Height (cm)', digits=(16, 2))
    width = fields.Float(string='Width (cm)', digits=(16, 2))
    length = fields.Float(string='Length (cm)', digits=(16, 2))

    # ===== TRACKING =====
    user_id = fields.Many2one(
        'res.users',
        string='Responsible',
        default=lambda self: self.env.user,
        tracking=True,
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
    )

    notes = fields.Text(string='Notes')

    # ===== IMPORT / INBOUND DOCUMENTS =====
    import_invoice_number = fields.Char(
        string='Import Invoice Number',
        help='Số hóa đơn nhập khẩu / Import invoice reference'
    )
    import_packing_list = fields.Char(
        string='Import Packing List',
        help='Phiếu đóng gói / Packing list reference'
    )
    import_bill_of_lading = fields.Char(
        string='Bill of Lading',
        help='Vận đơn / Bill of Lading reference'
    )

    # ===== COMPUTED FIELDS =====
    move_count = fields.Integer(compute='_compute_counts', string='Moves')
    quant_count = fields.Integer(compute='_compute_counts', string='Quants')
    product_count = fields.Integer(
        compute='_compute_product_count',
        string='Products',
        help="Number of different products in this batch"
    )

    @api.model
    def create(self, vals):
        """Generate sequence for batch number"""
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('hdi.batch') or _('New')
        return super().create(vals)

    @api.depends('quant_ids', 'quant_ids.quantity', 'quant_ids.reserved_quantity')
    def _compute_quantities(self):
        """
        ✅ QUAN TRỌNG: Số liệu tồn kho PHẢI từ stock.quant (core)
        Không tự tính toán riêng - luôn sync với core
        """
        for batch in self:
            batch.total_quantity = sum(batch.quant_ids.mapped('quantity'))
            batch.available_quantity = sum(
                quant.quantity - quant.reserved_quantity
                for quant in batch.quant_ids
            )
            batch.reserved_quantity = sum(batch.quant_ids.mapped('reserved_quantity'))

    @api.depends('quant_ids', 'product_id')
    def _compute_wms_status(self):
        """Determine batch status based on content"""
        for batch in self:
            if not batch.quant_ids or batch.total_quantity == 0:
                batch.wms_status = 'empty'
            elif len(batch.quant_ids.mapped('product_id')) > 1:
                batch.wms_status = 'mixed'
            elif batch.reserved_quantity > 0 and batch.available_quantity > 0:
                batch.wms_status = 'partial'
            else:
                batch.wms_status = 'full'

    @api.depends('move_ids', 'quant_ids')
    def _compute_counts(self):
        """Count related moves and quants"""
        for batch in self:
            batch.move_count = len(batch.move_ids)
            batch.quant_count = len(batch.quant_ids)

    @api.depends('quant_ids.product_id')
    def _compute_product_count(self):
        """Count distinct products in batch"""
        for batch in self:
            batch.product_count = len(batch.quant_ids.mapped('product_id'))

    def action_start_receiving(self):
        """Start receiving process"""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('Only draft batches can start receiving.'))
        self.state = 'in_receiving'

    def action_start_putaway(self):
        """Move batch to putaway process"""
        self.ensure_one()
        if self.state != 'in_receiving':
            raise UserError(_('Batch must be in receiving to start putaway.'))
        if not self.location_dest_id:
            # Trigger putaway suggestion
            return self.action_suggest_putaway()
        self.state = 'in_putaway'

    def action_confirm_storage(self):
        """
        Confirm batch is stored in final location
        ✅ Update stock.quant location (core operation)
        """
        self.ensure_one()
        if self.state != 'in_putaway':
            raise UserError(_('Batch must be in putaway to confirm storage.'))

        if not self.location_dest_id:
            raise UserError(_('Please set destination location first.'))

        # Update quants to destination location (CORE operation)
        for quant in self.quant_ids:
            if quant.location_id != self.location_dest_id:
                quant.location_id = self.location_dest_id

        self.location_id = self.location_dest_id
        self.state = 'stored'

    def action_suggest_putaway(self):
        """Open putaway suggestion wizard"""
        self.ensure_one()
        return {
            'name': _('Suggest Putaway Location'),
            'type': 'ir.actions.act_window',
            'res_model': 'hdi.putaway.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_batch_id': self.id,
                'default_product_id': self.product_id.id if self.product_id else False,
            }
        }

    def action_view_moves(self):
        """View all stock moves linked to this batch"""
        self.ensure_one()
        return {
            'name': _('Stock Moves'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.move',
            'view_mode': 'list,form',
            'domain': [('batch_id', '=', self.id)],
            'context': {'create': False},
        }

    def action_view_quants(self):
        """View all quants (inventory) in this batch"""
        self.ensure_one()
        return {
            'name': _('Inventory Quants'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.quant',
            'view_mode': 'list,form',
            'domain': [('batch_id', '=', self.id)],
            'context': {'create': False},
        }

    @api.constrains('barcode')
    def _check_unique_barcode(self):
        """Ensure barcode is unique"""
        for batch in self:
            if batch.barcode:
                duplicate = self.search([
                    ('id', '!=', batch.id),
                    ('barcode', '=', batch.barcode),
                    ('state', '!=', 'cancel'),
                ], limit=1)
                if duplicate:
                    raise ValidationError(_(
                        'Barcode %s is already used by batch %s'
                    ) % (batch.barcode, duplicate.name))

    def on_barcode_scanned(self, barcode):
        """Handle barcode scanning events"""
        # Implement scanning logic for mobile/handheld devices
        pass
