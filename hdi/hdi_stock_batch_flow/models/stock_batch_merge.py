from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class StockBatchMerge(models.Model):
    _name = 'stock.batch.merge'
    _description = 'Stock Batch Merge'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        tracking=True
    )
    source_lot_ids = fields.Many2many(
        'stock.lot',
        string='Source Lots/Batches',
        domain="[('product_id', '=', product_id)]"
    )
    target_lot_id = fields.Many2one(
        'stock.lot',
        string='Target Batch/Lot',
        tracking=True
    )
    target_lot_name = fields.Char(
        string='New Target Lot Name',
        help='Leave empty to use existing lot or enter name for new lot'
    )
    merge_line_ids = fields.One2many(
        'stock.batch.merge.line',
        'merge_id',
        string='Merge Lines'
    )
    total_quantity = fields.Float(
        string='Total Quantity',
        compute='_compute_total_quantity',
        store=True,
        digits='Product Unit of Measure'
    )
    uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        related='product_id.uom_id',
        readonly=True
    )
    location_id = fields.Many2one(
        'stock.location',
        string='Location',
        required=True,
        domain=[('usage', '=', 'internal')]
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ], string='Status', default='draft', tracking=True)
    date = fields.Datetime(
        string='Merge Date',
        default=fields.Datetime.now,
        required=True
    )
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )

    @api.depends('merge_line_ids.quantity')
    def _compute_total_quantity(self):
        for record in self:
            record.total_quantity = sum(record.merge_line_ids.mapped('quantity'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('stock.batch.merge') or _('New')
        return super().create(vals_list)

    @api.onchange('source_lot_ids')
    def _onchange_source_lots(self):
        """Auto-populate merge lines when source lots are selected"""
        if self.source_lot_ids:
            lines = []
            for lot in self.source_lot_ids:
                # Get available quantity for this lot at the location
                quant = self.env['stock.quant'].search([
                    ('lot_id', '=', lot.id),
                    ('location_id', '=', self.location_id.id),
                    ('product_id', '=', self.product_id.id),
                ], limit=1)
                
                quantity = quant.quantity if quant else 0.0
                lines.append((0, 0, {
                    'source_lot_id': lot.id,
                    'quantity': quantity,
                }))
            self.merge_line_ids = lines

    def action_confirm(self):
        self.ensure_one()
        if not self.merge_line_ids:
            raise UserError(_('Please add at least one merge line.'))
        
        # Check if all lots belong to same product
        products = self.merge_line_ids.mapped('source_lot_id.product_id')
        if len(products) > 1:
            raise UserError(_('All source lots must belong to the same product.'))
        
        self.state = 'confirmed'

    def action_done(self):
        self.ensure_one()
        if self.state != 'confirmed':
            raise UserError(_('Only confirmed merges can be processed.'))
        
        # Create or get target lot
        if self.target_lot_name and not self.target_lot_id:
            target_lot = self.env['stock.lot'].create({
                'name': self.target_lot_name,
                'product_id': self.product_id.id,
                'company_id': self.company_id.id,
            })
            self.target_lot_id = target_lot.id
        elif not self.target_lot_id:
            raise UserError(_('Please specify a target lot or provide a name for a new lot.'))
        
        self.state = 'done'
        return True

    def action_cancel(self):
        self.ensure_one()
        if self.state == 'done':
            raise UserError(_('Cannot cancel a completed merge.'))
        self.state = 'cancel'

    def action_draft(self):
        self.ensure_one()
        self.state = 'draft'


class StockBatchMergeLine(models.Model):
    _name = 'stock.batch.merge.line'
    _description = 'Stock Batch Merge Line'
    _order = 'sequence, id'

    sequence = fields.Integer(string='Sequence', default=10)
    merge_id = fields.Many2one(
        'stock.batch.merge',
        string='Merge Reference',
        required=True,
        ondelete='cascade'
    )
    source_lot_id = fields.Many2one(
        'stock.lot',
        string='Source Lot/Batch',
        required=True,
        domain="[('product_id', '=', product_id)]"
    )
    product_id = fields.Many2one(
        'product.product',
        related='merge_id.product_id',
        store=True,
        readonly=True
    )
    quantity = fields.Float(
        string='Quantity',
        required=True,
        digits='Product Unit of Measure'
    )
    available_quantity = fields.Float(
        string='Available Quantity',
        compute='_compute_available_quantity',
        digits='Product Unit of Measure'
    )
    notes = fields.Char(string='Notes')

    @api.depends('source_lot_id', 'merge_id.location_id')
    def _compute_available_quantity(self):
        for record in self:
            if record.source_lot_id and record.merge_id.location_id:
                quant = self.env['stock.quant'].search([
                    ('lot_id', '=', record.source_lot_id.id),
                    ('location_id', '=', record.merge_id.location_id.id),
                    ('product_id', '=', record.product_id.id),
                ], limit=1)
                record.available_quantity = quant.quantity if quant else 0.0
            else:
                record.available_quantity = 0.0

    @api.constrains('quantity', 'available_quantity')
    def _check_quantity(self):
        for record in self:
            if record.quantity <= 0:
                raise ValidationError(_('Quantity must be greater than zero.'))
            if record.quantity > record.available_quantity:
                raise ValidationError(_(
                    'Quantity (%s) cannot exceed available quantity (%s) for lot %s'
                ) % (record.quantity, record.available_quantity, record.source_lot_id.name))
