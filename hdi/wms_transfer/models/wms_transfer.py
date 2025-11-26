# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class WmsTransfer(models.Model):
    _name = 'wms.transfer'
    _description = 'WMS Internal Transfer'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(
        string='Transfer Number',
        required=True,
        readonly=True,
        default='/',
        copy=False,
        tracking=True
    )
    
    date = fields.Datetime(
        string='Transfer Date',
        required=True,
        default=fields.Datetime.now,
        tracking=True
    )
    
    scheduled_date = fields.Datetime(
        string='Scheduled Date',
        tracking=True
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ], string='Status', default='draft', required=True, tracking=True)
    
    # Source & Destination
    warehouse_id = fields.Many2one(
        'wms.warehouse',
        string='Warehouse',
        required=True,
        tracking=True
    )
    
    source_location_id = fields.Many2one(
        'wms.location',
        string='Source Location',
        required=True,
        tracking=True,
        domain="[('warehouse_id', '=', warehouse_id)]"
    )
    
    dest_location_id = fields.Many2one(
        'wms.location',
        string='Destination Location',
        required=True,
        tracking=True,
        domain="[('warehouse_id', '=', warehouse_id), ('id', '!=', source_location_id)]"
    )
    
    # Transfer Details
    transfer_type = fields.Selection([
        ('replenishment', 'Replenishment'),
        ('reorganization', 'Reorganization'),
        ('consolidation', 'Consolidation'),
        ('damage', 'Damaged Goods'),
        ('quarantine', 'To Quarantine'),
        ('return', 'Return to Storage'),
        ('other', 'Other')
    ], string='Transfer Type', required=True, default='replenishment', tracking=True)
    
    reason = fields.Text(
        string='Reason',
        tracking=True
    )
    
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Urgent'),
        ('2', 'Very Urgent')
    ], string='Priority', default='0', tracking=True)
    
    # Lines
    line_ids = fields.One2many(
        'wms.transfer.line',
        'transfer_id',
        string='Transfer Lines'
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
        'transfer_id',
        string='Stock Moves',
        readonly=True
    )
    
    # Computed
    total_lines = fields.Integer(
        string='Total Lines',
        compute='_compute_total_lines',
        store=True
    )
    
    notes = fields.Text(
        string='Notes'
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )

    @api.depends('line_ids')
    def _compute_total_lines(self):
        for record in self:
            record.total_lines = len(record.line_ids)

    @api.constrains('source_location_id', 'dest_location_id')
    def _check_locations(self):
        for record in self:
            if record.source_location_id == record.dest_location_id:
                raise ValidationError(_('Source and destination locations must be different.'))

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('wms.transfer') or '/'
        return super(WmsTransfer, self).create(vals)

    def action_submit(self):
        """Submit transfer for approval"""
        for record in self:
            if not record.line_ids:
                raise UserError(_('Cannot submit transfer without lines.'))
            record.state = 'pending'
            record.message_post(body=_('Transfer submitted for approval.'))

    def action_approve(self):
        """Approve transfer"""
        for record in self:
            record.write({
                'state': 'approved',
                'approved_by': self.env.user.id,
                'approved_date': fields.Datetime.now()
            })
            record.message_post(body=_('Transfer approved by %s.') % self.env.user.name)

    def action_reject(self):
        """Reject transfer"""
        for record in self:
            record.state = 'cancel'
            record.message_post(body=_('Transfer rejected by %s.') % self.env.user.name)

    def action_start(self):
        """Start transfer process"""
        for record in self:
            if record.state != 'approved':
                raise UserError(_('Only approved transfers can be started.'))
            
            # Reserve stock at source location
            for line in record.line_ids:
                line._reserve_stock()
            
            record.state = 'in_progress'
            record.message_post(body=_('Transfer started.'))

    def action_validate(self):
        """Validate and execute transfer"""
        for record in self:
            if record.state != 'in_progress':
                raise UserError(_('Only in-progress transfers can be validated.'))
            
            # Create stock moves for each line
            moves = self.env['wms.stock.move']
            for line in record.line_ids:
                if line.quantity_done <= 0:
                    raise UserError(_('Line %s has no quantity done.') % line.product_id.name)
                
                move_vals = {
                    'name': _('Transfer: %s') % record.name,
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.quantity_done,
                    'location_id': record.source_location_id.id,
                    'location_dest_id': record.dest_location_id.id,
                    'lot_id': line.lot_id.id if line.lot_id else False,
                    'move_type': 'transfer',
                    'origin': record.name,
                    'transfer_id': record.id,
                    'state': 'draft',
                }
                move = moves.create(move_vals)
                
                # Execute move: confirm → assign → done
                move.action_confirm()
                move.action_assign()
                move.action_done()
            
            record.state = 'done'
            record.message_post(body=_('Transfer completed successfully.'))

    def action_cancel(self):
        """Cancel transfer"""
        for record in self:
            if record.state == 'done':
                raise UserError(_('Cannot cancel completed transfers.'))
            
            # Unreserve stock if in progress
            if record.state == 'in_progress':
                for line in record.line_ids:
                    line._unreserve_stock()
            
            record.state = 'cancel'
            record.message_post(body=_('Transfer cancelled.'))

    def action_set_to_draft(self):
        """Reset to draft"""
        for record in self:
            if record.state not in ['cancel', 'pending']:
                raise UserError(_('Only cancelled or pending transfers can be reset to draft.'))
            record.state = 'draft'

    def unlink(self):
        for record in self:
            if record.state not in ['draft', 'cancel']:
                raise UserError(_('Cannot delete transfer in %s state.') % record.state)
        return super(WmsTransfer, self).unlink()


class WmsStockMove(models.Model):
    _inherit = 'wms.stock.move'

    transfer_id = fields.Many2one(
        'wms.transfer',
        string='Transfer',
        ondelete='cascade'
    )
