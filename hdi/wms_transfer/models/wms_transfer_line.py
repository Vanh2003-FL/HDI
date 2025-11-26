# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class WmsTransferLine(models.Model):
    _name = 'wms.transfer.line'
    _description = 'WMS Transfer Line'
    _order = 'id'

    transfer_id = fields.Many2one(
        'wms.transfer',
        string='Transfer',
        required=True,
        ondelete='cascade'
    )
    
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        domain=[('type', '=', 'product')]
    )
    
    lot_id = fields.Many2one(
        'stock.lot',
        string='Lot/Serial Number',
        domain="[('product_id', '=', product_id)]"
    )
    
    quantity = fields.Float(
        string='Quantity to Transfer',
        required=True,
        default=1.0,
        digits='Product Unit of Measure'
    )
    
    quantity_done = fields.Float(
        string='Quantity Done',
        default=0.0,
        digits='Product Unit of Measure'
    )
    
    quantity_available = fields.Float(
        string='Available Quantity',
        compute='_compute_quantity_available',
        digits='Product Unit of Measure'
    )
    
    availability_status = fields.Selection([
        ('unavailable', 'Unavailable'),
        ('partial', 'Partially Available'),
        ('available', 'Available')
    ], string='Availability', compute='_compute_availability_status', store=True)
    
    product_uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        related='product_id.uom_id',
        readonly=True
    )
    
    state = fields.Selection(
        related='transfer_id.state',
        string='Status',
        store=True
    )
    
    notes = fields.Text(
        string='Notes'
    )

    @api.depends('product_id', 'lot_id', 'transfer_id.source_location_id')
    def _compute_quantity_available(self):
        quant_obj = self.env['wms.stock.quant']
        for line in self:
            if not line.product_id or not line.transfer_id.source_location_id:
                line.quantity_available = 0.0
                continue
            
            domain = [
                ('product_id', '=', line.product_id.id),
                ('location_id', '=', line.transfer_id.source_location_id.id),
                ('status', '=', 'available')
            ]
            if line.lot_id:
                domain.append(('lot_id', '=', line.lot_id.id))
            
            quants = quant_obj.search(domain)
            line.quantity_available = sum(quants.mapped('available_quantity'))

    @api.depends('quantity', 'quantity_available')
    def _compute_availability_status(self):
        for line in self:
            if line.quantity_available <= 0:
                line.availability_status = 'unavailable'
            elif line.quantity_available < line.quantity:
                line.availability_status = 'partial'
            else:
                line.availability_status = 'available'

    @api.constrains('quantity', 'quantity_done')
    def _check_quantities(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(_('Quantity to transfer must be positive.'))
            if line.quantity_done < 0:
                raise ValidationError(_('Quantity done cannot be negative.'))
            if line.quantity_done > line.quantity:
                raise ValidationError(_('Quantity done cannot exceed quantity to transfer.'))

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id

    def _reserve_stock(self):
        """Reserve stock at source location"""
        self.ensure_one()
        quant_obj = self.env['wms.stock.quant']
        
        if not self.transfer_id.source_location_id:
            raise UserError(_('Source location not set.'))
        
        # Reserve stock
        reserved_qty = quant_obj._update_reserved_quantity(
            self.product_id,
            self.transfer_id.source_location_id,
            self.quantity,
            lot_id=self.lot_id
        )
        
        if reserved_qty < self.quantity:
            raise UserError(
                _('Cannot reserve %s %s for product %s. Only %s available.') % (
                    self.quantity,
                    self.product_uom_id.name,
                    self.product_id.name,
                    reserved_qty
                )
            )

    def _unreserve_stock(self):
        """Unreserve stock at source location"""
        self.ensure_one()
        quant_obj = self.env['wms.stock.quant']
        
        quant_obj._update_reserved_quantity(
            self.product_id,
            self.transfer_id.source_location_id,
            -self.quantity,  # Negative to unreserve
            lot_id=self.lot_id
        )

    def action_set_quantity_done(self):
        """Set quantity done to quantity to transfer"""
        for line in self:
            if line.state != 'in_progress':
                raise UserError(_('Can only set quantity done for in-progress transfers.'))
            line.quantity_done = line.quantity
