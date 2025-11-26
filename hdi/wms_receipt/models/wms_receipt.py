# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class WmsReceipt(models.Model):
    _name = 'wms.receipt'
    _description = 'WMS Goods Receipt'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, name desc'

    name = fields.Char(string='Receipt Number', required=True, default='New',
                      copy=False, readonly=True, index=True, tracking=True)
    
    # Supplier & Reference
    partner_id = fields.Many2one('res.partner', string='Supplier', required=True,
                                 tracking=True, states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order',
                                        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    origin = fields.Char(string='Source Document', tracking=True,
                        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    
    # Warehouse & Location
    warehouse_id = fields.Many2one('wms.warehouse', string='Warehouse', required=True,
                                   default=lambda self: self.env['ir.config_parameter'].sudo().get_param('wms_base.default_warehouse_id'),
                                   tracking=True, states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    receiving_location_id = fields.Many2one('wms.location', string='Receiving Location',
                                           required=True, tracking=True,
                                           domain="[('zone_id.zone_type', '=', 'receiving'), ('zone_id.warehouse_id', '=', warehouse_id)]",
                                           states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    
    # Dates
    date = fields.Datetime(string='Scheduled Date', required=True,
                          default=fields.Datetime.now, tracking=True,
                          states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    date_done = fields.Datetime(string='Receipt Date', copy=False, readonly=True)
    
    # Lines
    line_ids = fields.One2many('wms.receipt.line', 'receipt_id', string='Receipt Lines',
                               states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    line_count = fields.Integer(string='Line Count', compute='_compute_line_count')
    
    # Quality Check
    require_quality_check = fields.Boolean(string='Require Quality Check', default=False,
                                          states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    quality_check_status = fields.Selection([
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('passed', 'Passed'),
        ('failed', 'Failed'),
    ], string='QC Status', default='pending', tracking=True)
    quality_notes = fields.Text(string='Quality Check Notes')
    
    # Putaway
    putaway_strategy = fields.Selection([
        ('manual', 'Manual'),
        ('nearest', 'Nearest Available'),
        ('fifo', 'FIFO Location'),
        ('fefo', 'FEFO Location'),
        ('fixed', 'Fixed Location'),
    ], string='Putaway Strategy', default='nearest', required=True,
       states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    putaway_done = fields.Boolean(string='Putaway Done', default=False, copy=False)
    
    # State
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('arrived', 'Arrived'),
        ('quality_check', 'Quality Check'),
        ('ready_putaway', 'Ready for Putaway'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='draft', copy=False, index=True, tracking=True)
    
    # Statistics
    total_quantity = fields.Float(string='Total Quantity', compute='_compute_totals', store=True)
    received_quantity = fields.Float(string='Received Quantity', compute='_compute_totals', store=True)
    
    # Additional Info
    note = fields.Text(string='Notes')
    user_id = fields.Many2one('res.users', string='Responsible', default=lambda self: self.env.user,
                             tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                default=lambda self: self.env.company)
    
    color = fields.Integer(string='Color Index')

    @api.depends('line_ids')
    def _compute_line_count(self):
        for record in self:
            record.line_count = len(record.line_ids)

    @api.depends('line_ids.expected_qty', 'line_ids.received_qty')
    def _compute_totals(self):
        for record in self:
            record.total_quantity = sum(record.line_ids.mapped('expected_qty'))
            record.received_quantity = sum(record.line_ids.mapped('received_qty'))

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('wms.receipt') or 'New'
        return super().create(vals)

    def action_confirm(self):
        """Confirm receipt"""
        for receipt in self:
            if receipt.state != 'draft':
                raise UserError(_('Only draft receipts can be confirmed!'))
            if not receipt.line_ids:
                raise UserError(_('Please add at least one receipt line!'))
            receipt.write({'state': 'confirmed'})
            receipt.message_post(body=_('Receipt confirmed'))
        return True

    def action_set_arrived(self):
        """Mark goods as arrived"""
        for receipt in self:
            if receipt.state != 'confirmed':
                raise UserError(_('Only confirmed receipts can be marked as arrived!'))
            
            next_state = 'quality_check' if receipt.require_quality_check else 'ready_putaway'
            receipt.write({'state': next_state})
            receipt.message_post(body=_('Goods arrived'))
        return True

    def action_start_quality_check(self):
        """Start quality inspection"""
        for receipt in self:
            if receipt.state != 'quality_check':
                raise UserError(_('Receipt must be in quality check state!'))
            receipt.write({'quality_check_status': 'in_progress'})
            receipt.message_post(body=_('Quality check started'))
        return True

    def action_quality_pass(self):
        """Pass quality check"""
        for receipt in self:
            if receipt.state != 'quality_check':
                raise UserError(_('Receipt must be in quality check state!'))
            receipt.write({
                'quality_check_status': 'passed',
                'state': 'ready_putaway'
            })
            receipt.message_post(body=_('Quality check passed'))
        return True

    def action_quality_fail(self):
        """Fail quality check"""
        for receipt in self:
            if receipt.state != 'quality_check':
                raise UserError(_('Receipt must be in quality check state!'))
            receipt.write({'quality_check_status': 'failed'})
            receipt.message_post(body=_('Quality check failed'))
        return True

    def action_suggest_putaway(self):
        """Open putaway suggestion wizard"""
        self.ensure_one()
        if self.state != 'ready_putaway':
            raise UserError(_('Receipt must be ready for putaway!'))
        
        return {
            'name': _('Putaway Suggestions'),
            'type': 'ir.actions.act_window',
            'res_model': 'putaway.suggestion.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_receipt_id': self.id,
                'default_strategy': self.putaway_strategy,
            }
        }

    def action_create_putaway_moves(self):
        """Create stock moves for putaway"""
        self.ensure_one()
        if self.state != 'ready_putaway':
            raise UserError(_('Receipt must be ready for putaway!'))
        
        StockMove = self.env['wms.stock.move']
        moves_created = 0
        
        for line in self.line_ids.filtered(lambda l: l.received_qty > 0 and not l.putaway_location_id):
            # Get putaway location based on strategy
            putaway_location = self._get_putaway_location(line)
            
            if not putaway_location:
                raise UserError(_('No suitable location found for product: %s') % line.product_id.display_name)
            
            # Create stock move
            move = StockMove.create({
                'name': f'{self.name} - Putaway',
                'product_id': line.product_id.id,
                'product_uom_qty': line.received_qty,
                'quantity': line.received_qty,
                'location_id': self.receiving_location_id.id,
                'location_dest_id': putaway_location.id,
                'lot_id': line.lot_id.id if line.lot_id else False,
                'move_type': 'receipt',
                'origin': self.name,
                'receipt_id': self.id,
                'date': fields.Datetime.now(),
                'state': 'confirmed',
            })
            
            # Update line with putaway location
            line.write({'putaway_location_id': putaway_location.id})
            moves_created += 1
        
        if moves_created > 0:
            self.message_post(body=_('%d putaway moves created') % moves_created)
        
        return True

    def _get_putaway_location(self, line):
        """Get putaway location based on strategy"""
        Location = self.env['wms.location']
        
        # Base domain: storage zone, available status, has capacity
        domain = [
            ('zone_id.warehouse_id', '=', self.warehouse_id.id),
            ('zone_id.zone_type', '=', 'storage'),
            ('location_status', '=', 'available'),
            ('available_capacity', '>', 0),
        ]
        
        # Check product storage requirements
        if line.product_id.wms_storage_type == 'frozen':
            domain.append(('storage_category', '=', 'frozen'))
        elif line.product_id.wms_storage_type == 'refrigerated':
            domain.append(('storage_category', '=', 'refrigerated'))
        elif line.product_id.wms_hazardous:
            domain.append(('storage_category', '=', 'hazardous'))
        
        locations = Location.search(domain)
        
        if not locations:
            return False
        
        # Apply strategy
        if self.putaway_strategy == 'nearest':
            # Sort by zone sequence and location name
            return locations.sorted(lambda l: (l.zone_id.sequence, l.complete_name))[0]
        
        elif self.putaway_strategy == 'fifo':
            # Find location with oldest stock of same product
            return locations.sorted(lambda l: l.capacity_percentage)[0]
        
        elif self.putaway_strategy == 'fefo':
            # For FEFO, prefer locations with similar expiry products
            return locations.sorted(lambda l: l.capacity_percentage)[0]
        
        elif self.putaway_strategy == 'fixed':
            # Find designated location for this product (requires custom field)
            return locations[0]
        
        else:  # manual
            return False

    def action_validate_receipt(self):
        """Validate receipt and create stock"""
        for receipt in self:
            if receipt.state != 'ready_putaway':
                raise UserError(_('Receipt must be ready for putaway!'))
            
            # Check all lines have received quantity
            if any(line.received_qty == 0 for line in receipt.line_ids):
                raise UserError(_('All lines must have received quantity!'))
            
            # Create stock in receiving location
            StockQuant = self.env['wms.stock.quant']
            
            for line in receipt.line_ids:
                # Create or update stock quant in receiving location
                StockQuant._update_available_quantity(
                    product_id=line.product_id.id,
                    location_id=receipt.receiving_location_id.id,
                    quantity=line.received_qty,
                    lot_id=line.lot_id.id if line.lot_id else None,
                    in_date=fields.Datetime.now()
                )
            
            receipt.write({
                'state': 'done',
                'date_done': fields.Datetime.now()
            })
            receipt.message_post(body=_('Receipt validated - stock created in receiving location'))
        
        return True

    def action_cancel(self):
        """Cancel receipt"""
        for receipt in self:
            if receipt.state == 'done':
                raise UserError(_('Cannot cancel a completed receipt!'))
            receipt.write({'state': 'cancel'})
            receipt.message_post(body=_('Receipt cancelled'))
        return True

    def action_draft(self):
        """Set back to draft"""
        for receipt in self:
            if receipt.state not in ['cancel']:
                raise UserError(_('Only cancelled receipts can be reset to draft!'))
            receipt.write({'state': 'draft'})
        return True
