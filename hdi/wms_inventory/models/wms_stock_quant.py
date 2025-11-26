# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime


class WmsStockQuant(models.Model):
    _name = 'wms.stock.quant'
    _description = 'WMS Stock Quantity'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'complete_name'
    _order = 'location_id, product_id, lot_id, in_date'

    complete_name = fields.Char(string='Complete Name', compute='_compute_complete_name', store=True)
    
    # Product & Location
    product_id = fields.Many2one('product.product', string='Product', required=True,
                                 ondelete='restrict', index=True, tracking=True)
    product_tmpl_id = fields.Many2one('product.template', string='Product Template',
                                      related='product_id.product_tmpl_id', store=True)
    location_id = fields.Many2one('wms.location', string='Location', required=True,
                                  ondelete='restrict', index=True, tracking=True)
    warehouse_id = fields.Many2one('wms.warehouse', string='Warehouse',
                                   related='location_id.warehouse_id', store=True, index=True)
    zone_id = fields.Many2one('wms.zone', string='Zone',
                             related='location_id.zone_id', store=True, index=True)
    
    # Lot/Serial tracking
    lot_id = fields.Many2one('stock.lot', string='Lot/Serial Number',
                            ondelete='restrict', index=True)
    lot_name = fields.Char(string='Lot/Serial', related='lot_id.name', store=True)
    
    # Quantities
    quantity = fields.Float(string='Quantity', digits='Product Unit of Measure',
                           default=0.0, tracking=True)
    reserved_quantity = fields.Float(string='Reserved Qty', digits='Product Unit of Measure',
                                    default=0.0, tracking=True)
    available_quantity = fields.Float(string='Available Qty', compute='_compute_available_quantity',
                                     store=True, digits='Product Unit of Measure')
    
    # Unit of measure
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure',
                                     related='product_id.uom_id', store=True)
    
    # Dates for FIFO/FEFO
    in_date = fields.Datetime(string='Incoming Date', default=fields.Datetime.now,
                             index=True, tracking=True)
    expiration_date = fields.Date(string='Expiration Date', index=True)
    removal_date = fields.Date(string='Removal Date', compute='_compute_removal_date',
                              store=True, index=True,
                              help='Date to use for FEFO strategy')
    
    # Valuation
    cost = fields.Float(string='Unit Cost', digits='Product Price')
    value = fields.Float(string='Total Value', compute='_compute_value', store=True,
                        digits='Product Price')
    
    # Owner & Package
    owner_id = fields.Many2one('res.partner', string='Owner')
    package_id = fields.Many2one('stock.quant.package', string='Package')
    
    # Status
    status = fields.Selection([
        ('available', 'Available'),
        ('reserved', 'Reserved'),
        ('quarantine', 'Quarantine'),
        ('damaged', 'Damaged'),
    ], string='Status', default='available', tracking=True)
    
    # Additional info
    notes = fields.Text(string='Notes')
    
    _sql_constraints = [
        ('quantity_check', 'CHECK(quantity >= 0)', 'Stock quantity cannot be negative!'),
        ('reserved_check', 'CHECK(reserved_quantity >= 0)', 'Reserved quantity cannot be negative!'),
        ('reserved_vs_quantity', 'CHECK(reserved_quantity <= quantity)', 
         'Reserved quantity cannot exceed total quantity!'),
    ]

    @api.depends('product_id', 'location_id', 'lot_id', 'quantity')
    def _compute_complete_name(self):
        for record in self:
            parts = [record.product_id.display_name, record.location_id.complete_name]
            if record.lot_id:
                parts.append(f'Lot: {record.lot_name}')
            parts.append(f'Qty: {record.quantity}')
            record.complete_name = ' | '.join(parts)

    @api.depends('quantity', 'reserved_quantity')
    def _compute_available_quantity(self):
        for record in self:
            record.available_quantity = record.quantity - record.reserved_quantity

    @api.depends('expiration_date', 'product_id.wms_shelf_life_days')
    def _compute_removal_date(self):
        for record in self:
            if record.expiration_date:
                record.removal_date = record.expiration_date
            elif record.product_id.wms_shelf_life_days and record.in_date:
                # Calculate expiration based on shelf life
                from datetime import timedelta
                in_datetime = record.in_date
                expiry = in_datetime + timedelta(days=record.product_id.wms_shelf_life_days)
                record.removal_date = expiry.date()
            else:
                record.removal_date = False

    @api.depends('quantity', 'cost')
    def _compute_value(self):
        for record in self:
            record.value = record.quantity * record.cost

    @api.constrains('location_id', 'product_id')
    def _check_location_compatibility(self):
        for record in self:
            # Check storage category compatibility
            if record.location_id.storage_category == 'hazardous' and not record.product_id.wms_hazardous:
                raise ValidationError(_('Only hazardous products can be stored in hazardous locations!'))
            
            # Check temperature requirements
            if record.location_id.temperature_controlled:
                if record.product_id.wms_storage_type == 'frozen':
                    if record.location_id.max_temperature > -15:
                        raise ValidationError(_('Frozen products require temperature below -15°C!'))
                elif record.product_id.wms_storage_type == 'refrigerated':
                    if record.location_id.min_temperature < 2 or record.location_id.max_temperature > 8:
                        raise ValidationError(_('Refrigerated products require 2-8°C!'))

    @api.model
    def _get_available_quantity(self, product_id, location_id, lot_id=None, owner_id=None, strict=False):
        """Get available quantity for a product at a location"""
        domain = [
            ('product_id', '=', product_id),
            ('location_id', '=', location_id),
            ('status', '=', 'available'),
        ]
        if lot_id:
            domain.append(('lot_id', '=', lot_id))
        if owner_id:
            domain.append(('owner_id', '=', owner_id))
        
        quants = self.search(domain)
        return sum(quants.mapped('available_quantity'))

    @api.model
    def _update_available_quantity(self, product_id, location_id, quantity, lot_id=None,
                                   package_id=None, owner_id=None, in_date=None):
        """Update stock quantity - create or update quant"""
        # Find existing quant
        domain = [
            ('product_id', '=', product_id),
            ('location_id', '=', location_id),
        ]
        if lot_id:
            domain.append(('lot_id', '=', lot_id))
        if package_id:
            domain.append(('package_id', '=', package_id))
        if owner_id:
            domain.append(('owner_id', '=', owner_id))
        
        quant = self.search(domain, limit=1)
        
        if quant:
            # Update existing
            new_qty = quant.quantity + quantity
            if new_qty < 0:
                raise ValidationError(_('Not enough stock! Available: %s, Requested: %s') % 
                                    (quant.available_quantity, abs(quantity)))
            quant.write({'quantity': new_qty})
        else:
            # Create new quant
            if quantity < 0:
                raise ValidationError(_('Cannot create negative stock!'))
            
            vals = {
                'product_id': product_id,
                'location_id': location_id,
                'quantity': quantity,
                'lot_id': lot_id,
                'package_id': package_id,
                'owner_id': owner_id,
                'in_date': in_date or fields.Datetime.now(),
            }
            quant = self.create(vals)
        
        return quant

    @api.model
    def _update_reserved_quantity(self, product_id, location_id, quantity, lot_id=None,
                                  package_id=None, owner_id=None, strict=True):
        """Reserve or unreserve stock quantity"""
        domain = [
            ('product_id', '=', product_id),
            ('location_id', '=', location_id),
            ('status', '=', 'available'),
        ]
        if lot_id:
            domain.append(('lot_id', '=', lot_id))
        if package_id:
            domain.append(('package_id', '=', package_id))
        if owner_id:
            domain.append(('owner_id', '=', owner_id))
        
        quants = self.search(domain, order='in_date, id')
        
        remaining = quantity
        taken_quants = self.env['wms.stock.quant']
        
        for quant in quants:
            if remaining <= 0:
                break
            
            available = quant.available_quantity
            if available <= 0:
                continue
            
            to_reserve = min(remaining, available)
            quant.write({'reserved_quantity': quant.reserved_quantity + to_reserve})
            remaining -= to_reserve
            taken_quants |= quant
        
        if strict and remaining > 0:
            raise ValidationError(_('Not enough available stock to reserve! Shortage: %s') % remaining)
        
        return taken_quants

    def action_set_quarantine(self):
        self.write({'status': 'quarantine'})
        self.message_post(body=_('Stock moved to quarantine'))

    def action_set_available(self):
        self.write({'status': 'available'})
        self.message_post(body=_('Stock set as available'))

    def action_set_damaged(self):
        self.write({'status': 'damaged'})
        self.message_post(body=_('Stock marked as damaged'))
