from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class StockBatchSplit(models.Model):
    _name = 'stock.batch.split'
    _description = 'Stock Batch Split'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    source_lot_id = fields.Many2one(
        'stock.lot',
        string='Source Batch/Lot',
        required=True,
        tracking=True
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        related='source_lot_id.product_id',
        store=True,
        readonly=True
    )
    source_quantity = fields.Float(
        string='Source Quantity',
        required=True,
        digits='Product Unit of Measure',
        tracking=True
    )
    uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        related='product_id.uom_id',
        readonly=True
    )
    split_line_ids = fields.One2many(
        'stock.batch.split.line',
        'split_id',
        string='Split Lines'
    )
    total_split_quantity = fields.Float(
        string='Total Split Quantity',
        compute='_compute_total_split_quantity',
        store=True,
        digits='Product Unit of Measure'
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
        string='Split Date',
        default=fields.Datetime.now,
        required=True
    )
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )

    @api.depends('split_line_ids.quantity')
    def _compute_total_split_quantity(self):
        for record in self:
            record.total_split_quantity = sum(record.split_line_ids.mapped('quantity'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('stock.batch.split') or _('New')
        return super().create(vals_list)

    @api.constrains('source_quantity', 'total_split_quantity')
    def _check_split_quantity(self):
        for record in self:
            if record.total_split_quantity > record.source_quantity:
                raise ValidationError(_(
                    'Total split quantity (%s) cannot exceed source quantity (%s)'
                ) % (record.total_split_quantity, record.source_quantity))

    def action_confirm(self):
        self.ensure_one()
        if not self.split_line_ids:
            raise UserError(_('Please add at least one split line.'))
        if self.total_split_quantity != self.source_quantity:
            raise UserError(_(
                'Total split quantity (%s) must equal source quantity (%s)'
            ) % (self.total_split_quantity, self.source_quantity))
        self.state = 'confirmed'

    def action_done(self):
        self.ensure_one()
        if self.state != 'confirmed':
            raise UserError(_('Only confirmed splits can be processed.'))
        
        # Create new lots for split
        StockLot = self.env['stock.lot']
        for line in self.split_line_ids:
            if not line.new_lot_name:
                raise UserError(_('Please provide a lot name for all split lines.'))
            
            # Create new lot
            new_lot = StockLot.create({
                'name': line.new_lot_name,
                'product_id': self.product_id.id,
                'company_id': self.company_id.id,
            })
            line.new_lot_id = new_lot.id
        
        self.state = 'done'
        return True

    def action_cancel(self):
        self.ensure_one()
        if self.state == 'done':
            raise UserError(_('Cannot cancel a completed split.'))
        self.state = 'cancel'

    def action_draft(self):
        self.ensure_one()
        self.state = 'draft'


class StockBatchSplitLine(models.Model):
    _name = 'stock.batch.split.line'
    _description = 'Stock Batch Split Line'
    _order = 'sequence, id'

    sequence = fields.Integer(string='Sequence', default=10)
    split_id = fields.Many2one(
        'stock.batch.split',
        string='Split Reference',
        required=True,
        ondelete='cascade'
    )
    new_lot_name = fields.Char(
        string='New Lot/Batch Name',
        required=True
    )
    new_lot_id = fields.Many2one(
        'stock.lot',
        string='Created Lot',
        readonly=True
    )
    quantity = fields.Float(
        string='Quantity',
        required=True,
        digits='Product Unit of Measure'
    )
    notes = fields.Char(string='Notes')

    @api.constrains('quantity')
    def _check_quantity(self):
        for record in self:
            if record.quantity <= 0:
                raise ValidationError(_('Quantity must be greater than zero.'))
