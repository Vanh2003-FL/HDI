# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import qrcode
import io
import base64


class StockBatchSplit(models.Model):
    _name = 'stock.batch.split'
    _description = 'Stock Batch Split Operation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(string='Split Reference', required=True, copy=False,
                      default=lambda self: _('New'), readonly=True, tracking=True)
    
    # Parent batch
    parent_batch_id = fields.Many2one('stock.lot', string='Parent Batch/Lot',
                                     required=True, tracking=True,
                                     domain=[('product_id', '!=', False)],
                                     states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    product_id = fields.Many2one(related='parent_batch_id.product_id', string='Product',
                                 store=True, readonly=True)
    parent_quantity = fields.Float(string='Parent Quantity', digits='Product Unit of Measure',
                                  help='Available quantity in parent batch')
    
    # Warehouse context
    warehouse_id = fields.Many2one('wms.warehouse', string='Warehouse', required=True,
                                  default=lambda self: self.env['wms.warehouse'].search([], limit=1),
                                  tracking=True, states={'done': [('readonly', True)]})
    location_id = fields.Many2one('wms.location', string='Location',
                                 domain="[('warehouse_id', '=', warehouse_id)]",
                                 help='Location where split operation takes place')
    
    # Split details
    date = fields.Datetime(string='Split Date', required=True, default=fields.Datetime.now,
                          tracking=True, states={'done': [('readonly', True)]})
    reason = fields.Text(string='Split Reason', tracking=True,
                        states={'done': [('readonly', True)]})
    split_type = fields.Selection([
        ('manual', 'Manual Split'),
        ('pallet', 'Pallet Breakdown'),
        ('container', 'Container Breakdown'),
        ('repacking', 'Repacking'),
    ], string='Split Type', default='manual', required=True, tracking=True,
       states={'done': [('readonly', True)]})
    
    # Child batches
    child_batch_ids = fields.One2many('stock.batch.split.line', 'split_id',
                                     string='Child Batches',
                                     states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    child_count = fields.Integer(string='Child Count', compute='_compute_child_count')
    total_child_quantity = fields.Float(string='Total Child Qty', compute='_compute_totals',
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

    @api.depends('child_batch_ids')
    def _compute_child_count(self):
        for record in self:
            record.child_count = len(record.child_batch_ids)

    @api.depends('child_batch_ids.quantity')
    def _compute_totals(self):
        for record in self:
            record.total_child_quantity = sum(record.child_batch_ids.mapped('quantity'))

    @api.onchange('parent_batch_id', 'location_id')
    def _onchange_parent_batch(self):
        """Get available quantity from parent batch"""
        if self.parent_batch_id and self.location_id:
            quants = self.env['wms.stock.quant'].search([
                ('lot_id', '=', self.parent_batch_id.id),
                ('location_id', '=', self.location_id.id),
                ('status', '=', 'available'),
            ])
            self.parent_quantity = sum(quants.mapped('available_quantity'))
        elif self.parent_batch_id:
            # Get total available across all locations
            quants = self.env['wms.stock.quant'].search([
                ('lot_id', '=', self.parent_batch_id.id),
                ('status', '=', 'available'),
            ])
            self.parent_quantity = sum(quants.mapped('available_quantity'))

    @api.constrains('child_batch_ids', 'parent_quantity')
    def _check_quantities(self):
        """Validate total child quantity doesn't exceed parent"""
        for record in self:
            if record.total_child_quantity > record.parent_quantity:
                raise ValidationError(_(
                    'Total child quantity (%.2f) cannot exceed parent quantity (%.2f)!'
                ) % (record.total_child_quantity, record.parent_quantity))

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('stock.batch.split') or _('New')
        return super().create(vals)

    def action_confirm(self):
        """Confirm split operation"""
        for record in self:
            if record.state != 'draft':
                raise UserError(_('Only draft splits can be confirmed!'))
            
            if not record.child_batch_ids:
                raise UserError(_('Please add at least one child batch!'))
            
            if record.total_child_quantity != record.parent_quantity:
                raise UserError(_(
                    'Total child quantity (%.2f) must equal parent quantity (%.2f)!'
                ) % (record.total_child_quantity, record.parent_quantity))
            
            record.write({'state': 'confirmed'})
            record.message_post(body=_('Split operation confirmed'))
        
        return True

    def action_execute(self):
        """Execute split: Create new lots and adjust stock"""
        for record in self:
            if record.state != 'confirmed':
                raise UserError(_('Only confirmed splits can be executed!'))
            
            # Create new child lots
            StockLot = self.env['stock.lot']
            StockMove = self.env['wms.stock.move']
            
            for line in record.child_batch_ids:
                if not line.new_lot_id:
                    # Create new lot
                    new_lot = StockLot.create({
                        'name': line.new_lot_name,
                        'product_id': record.product_id.id,
                        'company_id': record.company_id.id,
                        'ref': f'Split from {record.parent_batch_id.name}',
                    })
                    line.write({'new_lot_id': new_lot.id})
                
                # Create stock move to transfer quantity from parent to child
                # This is a virtual move to update quant lot_id
                move = StockMove.create({
                    'name': f'{record.name} - Split Line',
                    'product_id': record.product_id.id,
                    'product_uom_qty': line.quantity,
                    'quantity': line.quantity,
                    'location_id': record.location_id.id,
                    'location_dest_id': record.location_id.id,  # Same location
                    'lot_id': record.parent_batch_id.id,
                    'new_lot_id': line.new_lot_id.id,  # New field needed in wms.stock.move
                    'move_type': 'batch_split',
                    'origin': record.name,
                    'batch_split_id': record.id,
                    'date': record.date,
                    'state': 'confirmed',
                })
                
                # Auto-execute move
                move.action_assign()
                move.action_done()
                
                line.write({'state': 'done'})
            
            record.write({'state': 'done'})
            record.message_post(body=_('Split operation completed successfully'))
        
        return True

    def action_cancel(self):
        """Cancel split operation"""
        for record in self:
            if record.state == 'done':
                raise UserError(_('Cannot cancel completed split operations!'))
            record.write({'state': 'cancel'})
            record.message_post(body=_('Split operation cancelled'))
        return True

    def action_draft(self):
        """Set back to draft"""
        for record in self:
            if record.state != 'cancel':
                raise UserError(_('Only cancelled splits can be reset to draft!'))
            record.write({'state': 'draft'})
        return True

    def action_open_child_batches(self):
        """View created child batches"""
        self.ensure_one()
        return {
            'name': _('Child Batches'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.lot',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.child_batch_ids.mapped('new_lot_id').ids)],
            'context': {'create': False}
        }


class StockBatchSplitLine(models.Model):
    _name = 'stock.batch.split.line'
    _description = 'Stock Batch Split Line'
    _order = 'sequence, id'

    sequence = fields.Integer(string='Sequence', default=10)
    split_id = fields.Many2one('stock.batch.split', string='Split Operation', required=True,
                              ondelete='cascade')
    
    # New batch details
    new_lot_name = fields.Char(string='New Batch Name', required=True)
    new_lot_id = fields.Many2one('stock.lot', string='Created Batch', readonly=True)
    quantity = fields.Float(string='Quantity', required=True, digits='Product Unit of Measure')
    
    # QR Code
    qr_code = fields.Binary(string='QR Code', compute='_compute_qr_code', store=True)
    
    # State
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
    ], string='Status', default='draft', readonly=True)
    
    note = fields.Char(string='Notes')

    @api.depends('new_lot_name')
    def _compute_qr_code(self):
        """Generate QR code for batch"""
        for record in self:
            if record.new_lot_name:
                qr = qrcode.QRCode(version=1, box_size=10, border=5)
                qr.add_data(record.new_lot_name)
                qr.make(fit=True)
                
                img = qr.make_image(fill_color="black", back_color="white")
                buffer = io.BytesIO()
                img.save(buffer, format='PNG')
                record.qr_code = base64.b64encode(buffer.getvalue())
            else:
                record.qr_code = False

    @api.constrains('quantity')
    def _check_quantity(self):
        for record in self:
            if record.quantity <= 0:
                raise ValidationError(_('Quantity must be greater than zero!'))
