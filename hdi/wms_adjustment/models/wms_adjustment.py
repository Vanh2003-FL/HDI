# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class WmsAdjustment(models.Model):
    _name = 'wms.adjustment'
    _description = 'WMS Inventory Adjustment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(
        string='Adjustment Number',
        required=True,
        readonly=True,
        default='/',
        copy=False,
        tracking=True
    )
    
    date = fields.Datetime(
        string='Date',
        required=True,
        default=fields.Datetime.now,
        tracking=True
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ], string='Status', default='draft', required=True, tracking=True)
    
    # Location
    warehouse_id = fields.Many2one(
        'wms.warehouse',
        string='Warehouse',
        required=True,
        tracking=True
    )
    
    location_id = fields.Many2one(
        'wms.location',
        string='Location',
        required=True,
        tracking=True,
        domain="[('warehouse_id', '=', warehouse_id)]"
    )
    
    # Adjustment Type
    adjustment_type = fields.Selection([
        ('increase', 'Increase Stock'),
        ('decrease', 'Decrease Stock'),
        ('cycle_count', 'Cycle Count'),
        ('physical', 'Physical Inventory'),
        ('correction', 'Correction')
    ], string='Adjustment Type', required=True, default='correction', tracking=True)
    
    reason_id = fields.Many2one(
        'wms.adjustment.reason',
        string='Reason',
        required=True,
        tracking=True
    )
    
    notes = fields.Text(
        string='Notes'
    )
    
    # Lines
    line_ids = fields.One2many(
        'wms.adjustment.line',
        'adjustment_id',
        string='Adjustment Lines'
    )
    
    # Responsible
    user_id = fields.Many2one(
        'res.users',
        string='Responsible',
        default=lambda self: self.env.user,
        tracking=True
    )
    
    approved_by = fields.Many2one(
        'res.users',
        string='Approved By',
        readonly=True,
        tracking=True
    )
    
    approved_date = fields.Datetime(
        string='Approved Date',
        readonly=True,
        tracking=True
    )
    
    # Stock Moves
    move_ids = fields.One2many(
        'wms.stock.move',
        'adjustment_id',
        string='Stock Moves',
        readonly=True
    )
    
    # Computed
    total_lines = fields.Integer(
        string='Total Lines',
        compute='_compute_totals',
        store=True
    )
    
    total_variance = fields.Float(
        string='Total Variance',
        compute='_compute_totals',
        store=True,
        help='Sum of absolute differences'
    )
    
    has_variance = fields.Boolean(
        string='Has Variance',
        compute='_compute_totals',
        store=True
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )

    @api.depends('line_ids', 'line_ids.variance_qty')
    def _compute_totals(self):
        for record in self:
            record.total_lines = len(record.line_ids)
            record.total_variance = sum(abs(line.variance_qty) for line in record.line_ids)
            record.has_variance = any(line.variance_qty != 0 for line in record.line_ids)

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('wms.adjustment') or '/'
        return super(WmsAdjustment, self).create(vals)

    def action_load_stock(self):
        """Load current stock quantities for location"""
        self.ensure_one()
        
        if self.state != 'draft':
            raise UserError(_('Can only load stock for draft adjustments.'))
        
        if self.line_ids:
            raise UserError(_('Adjustment already has lines. Clear them first.'))
        
        # Get stock from location
        quant_obj = self.env['wms.stock.quant']
        quants = quant_obj.search([
            ('location_id', '=', self.location_id.id),
            ('quantity', '>', 0)
        ])
        
        if not quants:
            raise UserError(_('No stock found in location %s.') % self.location_id.complete_name)
        
        # Create lines from quants
        for quant in quants:
            line_vals = {
                'adjustment_id': self.id,
                'product_id': quant.product_id.id,
                'lot_id': quant.lot_id.id if quant.lot_id else False,
                'theoretical_qty': quant.quantity,
                'counted_qty': 0.0,  # To be filled by user
            }
            self.env['wms.adjustment.line'].create(line_vals)
        
        self.message_post(body=_('Loaded %s products from location.') % len(quants))

    def action_submit(self):
        """Submit adjustment for approval"""
        for record in self:
            if not record.line_ids:
                raise UserError(_('Cannot submit adjustment without lines.'))
            
            # Check if counted quantities are filled (for cycle count/physical)
            if record.adjustment_type in ['cycle_count', 'physical']:
                unfilled_lines = record.line_ids.filtered(lambda l: l.counted_qty == 0)
                if unfilled_lines:
                    raise UserError(_('Please fill counted quantities for all lines.'))
            
            record.state = 'pending'
            record.message_post(body=_('Adjustment submitted for approval.'))

    def action_approve(self):
        """Approve adjustment"""
        for record in self:
            # Check variance threshold (can be configured)
            max_variance = 1000  # Example threshold
            if record.total_variance > max_variance:
                raise UserError(
                    _('Total variance (%s) exceeds approval threshold (%s). Manager review required.') % 
                    (record.total_variance, max_variance)
                )
            
            record.write({
                'state': 'approved',
                'approved_by': self.env.user.id,
                'approved_date': fields.Datetime.now()
            })
            record.message_post(body=_('Adjustment approved by %s.') % self.env.user.name)

    def action_reject(self):
        """Reject adjustment"""
        for record in self:
            record.state = 'cancel'
            record.message_post(body=_('Adjustment rejected by %s.') % self.env.user.name)

    def action_validate(self):
        """Validate and execute adjustment"""
        for record in self:
            if record.state != 'approved':
                raise UserError(_('Only approved adjustments can be validated.'))
            
            if not record.has_variance:
                record.state = 'done'
                record.message_post(body=_('No variance found. Adjustment completed without stock moves.'))
                continue
            
            # Create stock moves for variances
            moves = self.env['wms.stock.move']
            for line in record.line_ids.filtered(lambda l: l.variance_qty != 0):
                # Determine source and destination
                if line.variance_qty > 0:
                    # Increase: from adjustment location to storage
                    location_from = self.env.ref('stock.location_inventory')  # Virtual adjustment location
                    location_to = record.location_id
                    qty = line.variance_qty
                else:
                    # Decrease: from storage to adjustment location
                    location_from = record.location_id
                    location_to = self.env.ref('stock.location_inventory')
                    qty = abs(line.variance_qty)
                
                move_vals = {
                    'name': _('Adjustment: %s') % record.name,
                    'product_id': line.product_id.id,
                    'product_uom_qty': qty,
                    'location_id': location_from.id,
                    'location_dest_id': location_to.id,
                    'lot_id': line.lot_id.id if line.lot_id else False,
                    'move_type': 'adjustment',
                    'origin': record.name,
                    'adjustment_id': record.id,
                    'state': 'draft',
                }
                move = moves.create(move_vals)
                
                # Execute move
                move.action_confirm()
                if line.variance_qty < 0:
                    # For decrease, need to assign (reserve) first
                    move.action_assign()
                move.action_done()
            
            record.state = 'done'
            record.message_post(body=_('Adjustment validated successfully. %s moves created.') % len(moves))

    def action_cancel(self):
        """Cancel adjustment"""
        for record in self:
            if record.state == 'done':
                raise UserError(_('Cannot cancel completed adjustments.'))
            
            record.state = 'cancel'
            record.message_post(body=_('Adjustment cancelled.'))

    def action_set_to_draft(self):
        """Reset to draft"""
        for record in self:
            if record.state not in ['cancel', 'pending']:
                raise UserError(_('Only cancelled or pending adjustments can be reset to draft.'))
            record.state = 'draft'

    def unlink(self):
        for record in self:
            if record.state not in ['draft', 'cancel']:
                raise UserError(_('Cannot delete adjustment in %s state.') % record.state)
        return super(WmsAdjustment, self).unlink()


class WmsStockMove(models.Model):
    _inherit = 'wms.stock.move'

    adjustment_id = fields.Many2one(
        'wms.adjustment',
        string='Adjustment',
        ondelete='cascade'
    )
