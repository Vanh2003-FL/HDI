# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class StockBatchMerge(models.Model):
    _name = 'stock.batch.merge'
    _description = 'Stock Batch Merge Operation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(string='Merge Reference', required=True, copy=False,
                      default=lambda self: _('New'), readonly=True, tracking=True)
    
    # Product
    product_id = fields.Many2one('product.product', string='Product', required=True,
                                tracking=True, domain=[('type', '=', 'product')],
                                states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    
    # Warehouse context
    warehouse_id = fields.Many2one('wms.warehouse', string='Warehouse', required=True,
                                  default=lambda self: self.env['wms.warehouse'].search([], limit=1),
                                  tracking=True, states={'done': [('readonly', True)]})
    location_id = fields.Many2one('wms.location', string='Location',
                                 domain="[('warehouse_id', '=', warehouse_id)]",
                                 help='Location where merge operation takes place')
    
    # Merge details
    date = fields.Datetime(string='Merge Date', required=True, default=fields.Datetime.now,
                          tracking=True, states={'done': [('readonly', True)]})
    reason = fields.Text(string='Merge Reason', tracking=True,
                        states={'done': [('readonly', True)]})
    merge_type = fields.Selection([
        ('remnants', 'Merge Remnants'),
        ('consolidation', 'Stock Consolidation'),
        ('repacking', 'Repacking'),
        ('quality', 'Quality Batch Merge'),
    ], string='Merge Type', default='remnants', required=True, tracking=True,
       states={'done': [('readonly', True)]})
    
    # Source batches
    source_batch_ids = fields.One2many('stock.batch.merge.line', 'merge_id',
                                      string='Source Batches',
                                      states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    source_count = fields.Integer(string='Source Count', compute='_compute_source_count')
    total_source_quantity = fields.Float(string='Total Source Qty', compute='_compute_totals',
                                        digits='Product Unit of Measure', store=True)
    
    # Target batch
    target_batch_id = fields.Many2one('stock.lot', string='Target Batch', required=True,
                                     domain="[('product_id', '=', product_id)]",
                                     tracking=True,
                                     states={'done': [('readonly', True)]})
    create_new_target = fields.Boolean(string='Create New Target Batch', default=False,
                                      states={'done': [('readonly', True)]})
    new_target_name = fields.Char(string='New Target Batch Name',
                                  states={'done': [('readonly', True)]})
    target_quantity_before = fields.Float(string='Target Qty Before Merge',
                                         digits='Product Unit of Measure',
                                         help='Existing quantity in target batch')
    target_quantity_after = fields.Float(string='Target Qty After Merge',
                                        compute='_compute_target_after',
                                        digits='Product Unit of Measure', store=True)
    
    # State
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='draft', copy=False, tracking=True, index=True)
    
    # Additional info
    user_id = fields.Many2one('res.users', string='Responsible', default=lambda self: self.env.user,
                             tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                default=lambda self: self.env.company)
    note = fields.Text(string='Notes')

    @api.depends('source_batch_ids')
    def _compute_source_count(self):
        for record in self:
            record.source_count = len(record.source_batch_ids)

    @api.depends('source_batch_ids.quantity')
    def _compute_totals(self):
        for record in self:
            record.total_source_quantity = sum(record.source_batch_ids.mapped('quantity'))

    @api.depends('total_source_quantity', 'target_quantity_before')
    def _compute_target_after(self):
        for record in self:
            record.target_quantity_after = record.target_quantity_before + record.total_source_quantity

    @api.onchange('target_batch_id', 'location_id')
    def _onchange_target_batch(self):
        """Get available quantity from target batch"""
        if self.target_batch_id and self.location_id:
            quants = self.env['wms.stock.quant'].search([
                ('lot_id', '=', self.target_batch_id.id),
                ('location_id', '=', self.location_id.id),
                ('status', '=', 'available'),
            ])
            self.target_quantity_before = sum(quants.mapped('available_quantity'))
        elif self.target_batch_id:
            # Get total available across all locations
            quants = self.env['wms.stock.quant'].search([
                ('lot_id', '=', self.target_batch_id.id),
                ('status', '=', 'available'),
            ])
            self.target_quantity_before = sum(quants.mapped('available_quantity'))
        else:
            self.target_quantity_before = 0.0

    @api.onchange('create_new_target')
    def _onchange_create_new_target(self):
        """Clear target batch if creating new"""
        if self.create_new_target:
            self.target_batch_id = False
            if not self.new_target_name:
                self.new_target_name = f'MERGED-{fields.Date.today()}'

    @api.constrains('source_batch_ids', 'target_batch_id')
    def _check_batches(self):
        """Validate source batches are different from target"""
        for record in self:
            if record.target_batch_id:
                source_lot_ids = record.source_batch_ids.mapped('source_batch_id').ids
                if record.target_batch_id.id in source_lot_ids:
                    raise ValidationError(_('Target batch cannot be one of the source batches!'))

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('stock.batch.merge') or _('New')
        return super().create(vals)

    def action_confirm(self):
        """Confirm merge operation"""
        for record in self:
            if record.state != 'draft':
                raise UserError(_('Only draft merges can be confirmed!'))
            
            if not record.source_batch_ids:
                raise UserError(_('Please add at least two source batches!'))
            
            if len(record.source_batch_ids) < 2:
                raise UserError(_('Merge requires at least 2 source batches!'))
            
            if record.create_new_target and not record.new_target_name:
                raise UserError(_('Please specify new target batch name!'))
            
            if not record.create_new_target and not record.target_batch_id:
                raise UserError(_('Please specify target batch!'))
            
            record.write({'state': 'confirmed'})
            record.message_post(body=_('Merge operation confirmed'))
        
        return True

    def action_execute(self):
        """Execute merge: Transfer all source quantities to target batch"""
        for record in self:
            if record.state != 'confirmed':
                raise UserError(_('Only confirmed merges can be executed!'))
            
            StockLot = self.env['stock.lot']
            StockMove = self.env['wms.stock.move']
            
            # Create new target batch if needed
            if record.create_new_target:
                target_lot = StockLot.create({
                    'name': record.new_target_name,
                    'product_id': record.product_id.id,
                    'company_id': record.company_id.id,
                    'ref': f'Merged from {len(record.source_batch_ids)} batches',
                })
                record.write({'target_batch_id': target_lot.id})
            
            # Transfer stock from each source to target
            for line in record.source_batch_ids:
                # Create stock move to transfer quantity
                move = StockMove.create({
                    'name': f'{record.name} - Merge Line',
                    'product_id': record.product_id.id,
                    'product_uom_qty': line.quantity,
                    'quantity': line.quantity,
                    'location_id': record.location_id.id,
                    'location_dest_id': record.location_id.id,  # Same location
                    'lot_id': line.source_batch_id.id,
                    'target_lot_id': record.target_batch_id.id,  # New field needed in wms.stock.move
                    'move_type': 'batch_merge',
                    'origin': record.name,
                    'batch_merge_id': record.id,
                    'date': record.date,
                    'state': 'confirmed',
                })
                
                # Auto-execute move
                move.action_assign()
                move.action_done()
                
                line.write({'state': 'done'})
            
            record.write({'state': 'done'})
            record.message_post(body=_('Merge operation completed successfully. All quantities transferred to %s') % record.target_batch_id.name)
        
        return True

    def action_cancel(self):
        """Cancel merge operation"""
        for record in self:
            if record.state == 'done':
                raise UserError(_('Cannot cancel completed merge operations!'))
            record.write({'state': 'cancel'})
            record.message_post(body=_('Merge operation cancelled'))
        return True

    def action_draft(self):
        """Set back to draft"""
        for record in self:
            if record.state != 'cancel':
                raise UserError(_('Only cancelled merges can be reset to draft!'))
            record.write({'state': 'draft'})
        return True

    def action_open_target_batch(self):
        """View target batch"""
        self.ensure_one()
        return {
            'name': _('Target Batch'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.lot',
            'view_mode': 'form',
            'res_id': self.target_batch_id.id,
            'context': {'create': False}
        }


class StockBatchMergeLine(models.Model):
    _name = 'stock.batch.merge.line'
    _description = 'Stock Batch Merge Line'
    _order = 'sequence, id'

    sequence = fields.Integer(string='Sequence', default=10)
    merge_id = fields.Many2one('stock.batch.merge', string='Merge Operation', required=True,
                              ondelete='cascade')
    
    # Source batch
    source_batch_id = fields.Many2one('stock.lot', string='Source Batch', required=True,
                                     domain="[('product_id', '=', product_id)]")
    product_id = fields.Many2one(related='merge_id.product_id', string='Product', store=True)
    quantity = fields.Float(string='Quantity to Merge', required=True,
                           digits='Product Unit of Measure')
    available_quantity = fields.Float(string='Available Qty', digits='Product Unit of Measure',
                                     help='Available quantity in source batch')
    
    # State
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
    ], string='Status', default='draft', readonly=True)
    
    note = fields.Char(string='Notes')

    @api.onchange('source_batch_id')
    def _onchange_source_batch(self):
        """Get available quantity from source batch"""
        if self.source_batch_id and self.merge_id.location_id:
            quants = self.env['wms.stock.quant'].search([
                ('lot_id', '=', self.source_batch_id.id),
                ('location_id', '=', self.merge_id.location_id.id),
                ('status', '=', 'available'),
            ])
            self.available_quantity = sum(quants.mapped('available_quantity'))
            self.quantity = self.available_quantity
        elif self.source_batch_id:
            quants = self.env['wms.stock.quant'].search([
                ('lot_id', '=', self.source_batch_id.id),
                ('status', '=', 'available'),
            ])
            self.available_quantity = sum(quants.mapped('available_quantity'))
            self.quantity = self.available_quantity

    @api.constrains('quantity', 'available_quantity')
    def _check_quantity(self):
        for record in self:
            if record.quantity <= 0:
                raise ValidationError(_('Quantity must be greater than zero!'))
            if record.quantity > record.available_quantity:
                raise ValidationError(_(
                    'Quantity to merge (%.2f) cannot exceed available quantity (%.2f)!'
                ) % (record.quantity, record.available_quantity))
