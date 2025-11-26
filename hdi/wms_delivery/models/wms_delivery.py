# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class WmsDelivery(models.Model):
    _name = 'wms.delivery'
    _description = 'WMS Delivery Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, name desc'

    name = fields.Char(string='Delivery Number', required=True, default='New',
                      copy=False, readonly=True, index=True, tracking=True)
    
    # Customer & Reference
    partner_id = fields.Many2one('res.partner', string='Customer', required=True,
                                 tracking=True, states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    sale_order_id = fields.Many2one('sale.order', string='Sales Order',
                                    states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    origin = fields.Char(string='Source Document', tracking=True,
                        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    
    # Warehouse & Locations
    warehouse_id = fields.Many2one('wms.warehouse', string='Warehouse', required=True,
                                   default=lambda self: self.env['ir.config_parameter'].sudo().get_param('wms_base.default_warehouse_id'),
                                   tracking=True, states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    picking_location_id = fields.Many2one('wms.location', string='Picking Location',
                                         domain="[('zone_id.zone_type', '=', 'picking'), ('zone_id.warehouse_id', '=', warehouse_id)]",
                                         states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    packing_location_id = fields.Many2one('wms.location', string='Packing Location',
                                         domain="[('zone_id.zone_type', '=', 'packing'), ('zone_id.warehouse_id', '=', warehouse_id)]",
                                         states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    shipping_location_id = fields.Many2one('wms.location', string='Shipping Location',
                                          required=True,
                                          domain="[('zone_id.zone_type', '=', 'shipping'), ('zone_id.warehouse_id', '=', warehouse_id)]",
                                          states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    
    # Dates
    date = fields.Datetime(string='Scheduled Date', required=True,
                          default=fields.Datetime.now, tracking=True,
                          states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    date_done = fields.Datetime(string='Delivery Date', copy=False, readonly=True)
    
    # Lines
    line_ids = fields.One2many('wms.delivery.line', 'delivery_id', string='Delivery Lines',
                               states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    line_count = fields.Integer(string='Line Count', compute='_compute_line_count')
    
    # Picking Strategy
    picking_strategy = fields.Selection([
        ('fifo', 'FIFO - First In First Out'),
        ('fefo', 'FEFO - First Expired First Out'),
        ('lifo', 'LIFO - Last In First Out'),
        ('nearest', 'Nearest Location'),
    ], string='Picking Strategy', default='fifo', required=True,
       states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    
    # Wave Management
    wave_id = fields.Char(string='Wave ID', help='For batch picking')
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Urgent'),
        ('2', 'Very Urgent'),
    ], string='Priority', default='0', tracking=True)
    
    # State
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('assigned', 'Assigned'),
        ('picking', 'Picking'),
        ('picked', 'Picked'),
        ('packing', 'Packing'),
        ('ready_ship', 'Ready to Ship'),
        ('shipped', 'Shipped'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='draft', copy=False, index=True, tracking=True)
    
    # Statistics
    total_quantity = fields.Float(string='Total Quantity', compute='_compute_totals', store=True)
    picked_quantity = fields.Float(string='Picked Quantity', compute='_compute_totals', store=True)
    
    # Shipping
    carrier_id = fields.Many2one('delivery.carrier', string='Carrier')
    tracking_number = fields.Char(string='Tracking Number', copy=False)
    weight = fields.Float(string='Weight (kg)', digits=(12, 2))
    
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

    @api.depends('line_ids.ordered_qty', 'line_ids.picked_qty')
    def _compute_totals(self):
        for record in self:
            record.total_quantity = sum(record.line_ids.mapped('ordered_qty'))
            record.picked_quantity = sum(record.line_ids.mapped('picked_qty'))

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('wms.delivery') or 'New'
        return super().create(vals)

    def action_confirm(self):
        """Confirm delivery"""
        for delivery in self:
            if delivery.state != 'draft':
                raise UserError(_('Only draft deliveries can be confirmed!'))
            if not delivery.line_ids:
                raise UserError(_('Please add at least one delivery line!'))
            delivery.write({'state': 'confirmed'})
            delivery.message_post(body=_('Delivery confirmed'))
        return True

    def action_assign(self):
        """Check availability and reserve stock"""
        for delivery in self:
            if delivery.state != 'confirmed':
                raise UserError(_('Only confirmed deliveries can be assigned!'))
            
            StockQuant = self.env['wms.stock.quant']
            all_available = True
            
            for line in delivery.line_ids:
                # Find available stock based on strategy
                locations_with_stock = self._find_stock_for_picking(line)
                
                if not locations_with_stock:
                    all_available = False
                    line.write({'availability_status': 'unavailable'})
                    continue
                
                # Reserve stock
                qty_to_reserve = line.ordered_qty
                for location_id, available_qty in locations_with_stock:
                    if qty_to_reserve <= 0:
                        break
                    
                    to_reserve = min(qty_to_reserve, available_qty)
                    StockQuant._update_reserved_quantity(
                        line.product_id.id,
                        location_id,
                        to_reserve,
                        strict=False
                    )
                    
                    # Create picking line
                    line.picking_line_ids.create({
                        'delivery_line_id': line.id,
                        'location_id': location_id,
                        'quantity': to_reserve,
                        'status': 'assigned',
                    })
                    
                    qty_to_reserve -= to_reserve
                
                if qty_to_reserve > 0:
                    line.write({'availability_status': 'partial'})
                    all_available = False
                else:
                    line.write({'availability_status': 'available'})
            
            if all_available:
                delivery.write({'state': 'assigned'})
                delivery.message_post(body=_('Stock fully assigned'))
            else:
                delivery.write({'state': 'assigned'})
                delivery.message_post(body=_('Stock partially assigned'), message_type='warning')
        
        return True

    def _find_stock_for_picking(self, line):
        """Find stock locations based on picking strategy"""
        StockQuant = self.env['wms.stock.quant']
        
        domain = [
            ('product_id', '=', line.product_id.id),
            ('status', '=', 'available'),
            ('available_quantity', '>', 0),
            ('zone_id.zone_type', '=', 'storage'),
            ('zone_id.warehouse_id', '=', self.warehouse_id.id),
        ]
        
        if self.picking_strategy == 'fifo':
            quants = StockQuant.search(domain, order='in_date, id')
        elif self.picking_strategy == 'fefo':
            quants = StockQuant.search(domain, order='removal_date, in_date, id')
        elif self.picking_strategy == 'lifo':
            quants = StockQuant.search(domain, order='in_date desc, id desc')
        else:  # nearest
            quants = StockQuant.search(domain, order='location_id, id')
        
        # Return list of (location_id, available_qty)
        result = []
        for quant in quants:
            if quant.available_quantity > 0:
                result.append((quant.location_id.id, quant.available_quantity))
        
        return result

    def action_start_picking(self):
        """Start picking process"""
        for delivery in self:
            if delivery.state != 'assigned':
                raise UserError(_('Only assigned deliveries can start picking!'))
            delivery.write({'state': 'picking'})
            delivery.message_post(body=_('Picking started'))
        return True

    def action_validate_picking(self):
        """Validate picked quantities"""
        for delivery in self:
            if delivery.state != 'picking':
                raise UserError(_('Only picking deliveries can be validated!'))
            
            # Check all lines picked
            if any(line.picked_qty == 0 for line in delivery.line_ids):
                raise UserError(_('All lines must have picked quantity!'))
            
            # Create moves from storage to picking/packing location
            StockMove = self.env['wms.stock.move']
            dest_location = delivery.packing_location_id or delivery.shipping_location_id
            
            for line in delivery.line_ids:
                for pick_line in line.picking_line_ids:
                    if pick_line.quantity > 0:
                        move = StockMove.create({
                            'name': f'{delivery.name} - Pick',
                            'product_id': line.product_id.id,
                            'product_uom_qty': pick_line.quantity,
                            'quantity': pick_line.quantity,
                            'location_id': pick_line.location_id.id,
                            'location_dest_id': dest_location.id,
                            'move_type': 'delivery',
                            'origin': delivery.name,
                            'delivery_id': delivery.id,
                            'date': fields.Datetime.now(),
                            'state': 'confirmed',
                        })
                        # Auto-assign and execute
                        move.action_assign()
                        move.action_done()
            
            next_state = 'packing' if delivery.packing_location_id else 'ready_ship'
            delivery.write({'state': next_state})
            delivery.message_post(body=_('Picking validated'))
        
        return True

    def action_start_packing(self):
        """Start packing"""
        for delivery in self:
            if delivery.state != 'packing':
                raise UserError(_('Delivery must be in packing state!'))
            delivery.message_post(body=_('Packing started'))
        return True

    def action_validate_packing(self):
        """Complete packing"""
        for delivery in self:
            if delivery.state != 'packing':
                raise UserError(_('Delivery must be in packing state!'))
            
            # Move to shipping location if different
            if delivery.shipping_location_id != delivery.packing_location_id:
                StockMove = self.env['wms.stock.move']
                for line in delivery.line_ids:
                    move = StockMove.create({
                        'name': f'{delivery.name} - Pack',
                        'product_id': line.product_id.id,
                        'product_uom_qty': line.picked_qty,
                        'quantity': line.picked_qty,
                        'location_id': delivery.packing_location_id.id,
                        'location_dest_id': delivery.shipping_location_id.id,
                        'move_type': 'delivery',
                        'origin': delivery.name,
                        'delivery_id': delivery.id,
                        'date': fields.Datetime.now(),
                        'state': 'confirmed',
                    })
                    move.action_assign()
                    move.action_done()
            
            delivery.write({'state': 'ready_ship'})
            delivery.message_post(body=_('Packing completed'))
        
        return True

    def action_ship(self):
        """Mark as shipped"""
        for delivery in self:
            if delivery.state != 'ready_ship':
                raise UserError(_('Delivery must be ready to ship!'))
            
            delivery.write({
                'state': 'shipped',
                'date_done': fields.Datetime.now()
            })
            delivery.message_post(body=_('Shipment sent'))
        
        return True

    def action_done(self):
        """Complete delivery"""
        for delivery in self:
            if delivery.state != 'shipped':
                raise UserError(_('Delivery must be shipped first!'))
            
            delivery.write({'state': 'done'})
            delivery.message_post(body=_('Delivery completed'))
        
        return True

    def action_cancel(self):
        """Cancel delivery and unreserve stock"""
        for delivery in self:
            if delivery.state == 'done':
                raise UserError(_('Cannot cancel a completed delivery!'))
            
            # Unreserve stock
            if delivery.state in ['assigned', 'picking']:
                StockQuant = self.env['wms.stock.quant']
                for line in delivery.line_ids:
                    for pick_line in line.picking_line_ids:
                        if pick_line.status != 'picked':
                            StockQuant._update_reserved_quantity(
                                line.product_id.id,
                                pick_line.location_id.id,
                                -pick_line.quantity,
                                strict=False
                            )
            
            delivery.write({'state': 'cancel'})
            delivery.message_post(body=_('Delivery cancelled'))
        
        return True
