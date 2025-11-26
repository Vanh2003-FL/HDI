# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class WmsStockMove(models.Model):
    _name = 'wms.stock.move'
    _description = 'WMS Stock Movement'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(string='Reference', required=True, default='New', copy=False,
                      readonly=True, index=True, tracking=True)
    
    # Product
    product_id = fields.Many2one('product.product', string='Product', required=True,
                                 ondelete='restrict', index=True, tracking=True,
                                 states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    product_tmpl_id = fields.Many2one('product.template', string='Product Template',
                                      related='product_id.product_tmpl_id', store=True)
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure',
                                     related='product_id.uom_id', store=True)
    
    # Locations
    location_id = fields.Many2one('wms.location', string='Source Location', required=True,
                                  index=True, tracking=True,
                                  states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    location_dest_id = fields.Many2one('wms.location', string='Destination Location', required=True,
                                       index=True, tracking=True,
                                       states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    
    # Lot/Serial
    lot_id = fields.Many2one('stock.lot', string='Lot/Serial Number',
                            index=True, states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    
    # Quantities
    product_uom_qty = fields.Float(string='Demand', digits='Product Unit of Measure',
                                  required=True, default=1.0, tracking=True,
                                  states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    quantity = fields.Float(string='Quantity Done', digits='Product Unit of Measure',
                           default=0.0, copy=False)
    
    # Dates
    date = fields.Datetime(string='Scheduled Date', required=True,
                          default=fields.Datetime.now, index=True, tracking=True,
                          states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    date_done = fields.Datetime(string='Date Done', copy=False, readonly=True)
    
    # State
    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting', 'Waiting'),
        ('confirmed', 'Confirmed'),
        ('assigned', 'Assigned'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='draft', copy=False, index=True, tracking=True)
    
    # Move type
    move_type = fields.Selection([
        ('receipt', 'Receipt'),
        ('delivery', 'Delivery'),
        ('transfer', 'Internal Transfer'),
        ('adjustment', 'Adjustment'),
    ], string='Move Type', required=True, tracking=True,
       states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    
    # References
    origin = fields.Char(string='Source Document', index=True,
                        help='Reference to the document that generated this move')
    receipt_id = fields.Many2one('wms.receipt', string='Receipt', ondelete='cascade')
    delivery_id = fields.Many2one('wms.delivery', string='Delivery', ondelete='cascade')
    transfer_id = fields.Many2one('wms.transfer', string='Transfer', ondelete='cascade')
    adjustment_id = fields.Many2one('wms.adjustment', string='Adjustment', ondelete='cascade')
    
    # Traceability
    move_line_ids = fields.One2many('wms.stock.move.line', 'move_id', string='Move Lines')
    quant_ids = fields.Many2many('wms.stock.quant', string='Stock Quants',
                                 compute='_compute_quant_ids')
    
    # Additional info
    note = fields.Text(string='Notes')
    user_id = fields.Many2one('res.users', string='Responsible', default=lambda self: self.env.user,
                             tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                default=lambda self: self.env.company)
    
    @api.depends('move_line_ids.quant_id')
    def _compute_quant_ids(self):
        for record in self:
            record.quant_ids = record.move_line_ids.mapped('quant_id')

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('wms.stock.move') or 'New'
        return super().create(vals)

    @api.constrains('location_id', 'location_dest_id')
    def _check_locations(self):
        for record in self:
            if record.location_id == record.location_dest_id:
                raise ValidationError(_('Source and destination locations must be different!'))

    @api.constrains('product_uom_qty', 'quantity')
    def _check_quantities(self):
        for record in self:
            if record.product_uom_qty <= 0:
                raise ValidationError(_('Demand quantity must be positive!'))
            if record.quantity < 0:
                raise ValidationError(_('Done quantity cannot be negative!'))

    def action_confirm(self):
        """Confirm the move"""
        for move in self:
            if move.state not in ['draft', 'waiting']:
                raise UserError(_('Only draft or waiting moves can be confirmed!'))
            move.write({'state': 'confirmed'})
            move.message_post(body=_('Move confirmed'))
        return True

    def action_assign(self):
        """Check availability and reserve stock"""
        for move in self:
            if move.state not in ['confirmed', 'waiting']:
                raise UserError(_('Only confirmed moves can be assigned!'))
            
            # Check available quantity at source location
            available = self.env['wms.stock.quant']._get_available_quantity(
                move.product_id.id,
                move.location_id.id,
                lot_id=move.lot_id.id if move.lot_id else None
            )
            
            if available < move.product_uom_qty:
                raise UserError(_('Not enough stock available!\nRequired: %s\nAvailable: %s') % 
                              (move.product_uom_qty, available))
            
            # Reserve stock
            self.env['wms.stock.quant']._update_reserved_quantity(
                move.product_id.id,
                move.location_id.id,
                move.product_uom_qty,
                lot_id=move.lot_id.id if move.lot_id else None
            )
            
            move.write({'state': 'assigned'})
            move.message_post(body=_('Stock reserved'))
        return True

    def action_done(self):
        """Execute the move"""
        for move in self:
            if move.state != 'assigned':
                raise UserError(_('Only assigned moves can be done!'))
            
            if move.quantity <= 0:
                raise UserError(_('Please set the done quantity!'))
            
            # Unreserve if needed
            if move.quantity != move.product_uom_qty:
                diff = move.product_uom_qty - move.quantity
                self.env['wms.stock.quant']._update_reserved_quantity(
                    move.product_id.id,
                    move.location_id.id,
                    -diff,
                    lot_id=move.lot_id.id if move.lot_id else None,
                    strict=False
                )
            
            # Move stock from source to destination
            # 1. Remove from source
            self.env['wms.stock.quant']._update_available_quantity(
                move.product_id.id,
                move.location_id.id,
                -move.quantity,
                lot_id=move.lot_id.id if move.lot_id else None
            )
            
            # 2. Unreserve
            self.env['wms.stock.quant']._update_reserved_quantity(
                move.product_id.id,
                move.location_id.id,
                -move.quantity,
                lot_id=move.lot_id.id if move.lot_id else None,
                strict=False
            )
            
            # 3. Add to destination
            self.env['wms.stock.quant']._update_available_quantity(
                move.product_id.id,
                move.location_dest_id.id,
                move.quantity,
                lot_id=move.lot_id.id if move.lot_id else None,
                in_date=move.date
            )
            
            move.write({
                'state': 'done',
                'date_done': fields.Datetime.now()
            })
            move.message_post(body=_('Move completed: %s %s from %s to %s') % 
                            (move.quantity, move.product_uom_id.name,
                             move.location_id.complete_name, move.location_dest_id.complete_name))
        return True

    def action_cancel(self):
        """Cancel the move and unreserve stock"""
        for move in self:
            if move.state == 'done':
                raise UserError(_('Cannot cancel a done move!'))
            
            # Unreserve if assigned
            if move.state == 'assigned':
                self.env['wms.stock.quant']._update_reserved_quantity(
                    move.product_id.id,
                    move.location_id.id,
                    -move.product_uom_qty,
                    lot_id=move.lot_id.id if move.lot_id else None,
                    strict=False
                )
            
            move.write({'state': 'cancel'})
            move.message_post(body=_('Move cancelled'))
        return True

    def action_draft(self):
        """Set back to draft"""
        for move in self:
            if move.state not in ['cancel']:
                raise UserError(_('Only cancelled moves can be reset to draft!'))
            move.write({'state': 'draft'})
        return True


class WmsStockMoveLine(models.Model):
    _name = 'wms.stock.move.line'
    _description = 'WMS Stock Move Line'
    _order = 'move_id, id'

    move_id = fields.Many2one('wms.stock.move', string='Stock Move', required=True,
                             ondelete='cascade', index=True)
    product_id = fields.Many2one('product.product', related='move_id.product_id', store=True)
    quant_id = fields.Many2one('wms.stock.quant', string='Stock Quant')
    lot_id = fields.Many2one('stock.lot', string='Lot/Serial')
    quantity = fields.Float(string='Quantity', digits='Product Unit of Measure')
    location_id = fields.Many2one('wms.location', string='From Location')
    location_dest_id = fields.Many2one('wms.location', string='To Location')
