# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class BatchCreationWizard(models.TransientModel):
    _name = 'hdi.batch.creation.wizard'
    _description = 'Batch Creation Wizard'
    
    picking_id = fields.Many2one(
        'stock.picking',
        string='Picking',
        required=True,
        default=lambda self: self.env.context.get('default_picking_id'),
    )
    
    batch_type = fields.Selection([
        ('pallet', 'Pallet'),
        ('lpn', 'LPN'),
        ('container', 'Container'),
    ], string='Batch Type', default='pallet', required=True)
    
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        help="Leave empty for mixed product batch"
    )
    
    quantity = fields.Float(
        string='Quantity',
        digits='Product Unit of Measure',
    )
    
    location_id = fields.Many2one(
        'stock.location',
        string='Current Location',
        required=True,
    )
    
    auto_generate_barcode = fields.Boolean(
        string='Auto Generate Barcode',
        default=True,
    )
    
    barcode = fields.Char(string='Barcode/LPN')
    
    weight = fields.Float(string='Weight (kg)')
    volume = fields.Float(string='Volume (m³)')
    
    def action_create_batch(self):
        """Create batch and link to picking"""
        self.ensure_one()
        
        # Prepare values
        vals = {
            'picking_id': self.picking_id.id,
            'batch_type': self.batch_type,
            'product_id': self.product_id.id if self.product_id else False,
            'location_id': self.location_id.id,
            'weight': self.weight,
            'volume': self.volume,
            'state': 'in_receiving',
            'company_id': self.picking_id.company_id.id,
        }
        
        if self.barcode:
            vals['barcode'] = self.barcode
        
        # Create batch
        batch = self.env['hdi.batch'].create(vals)
        
        # Update picking WMS state
        if self.picking_id.wms_state == 'none':
            self.picking_id.wms_state = 'batch_creation'
        
        # Return to batch form
        return {
            'name': _('Batch Created'),
            'type': 'ir.actions.act_window',
            'res_model': 'hdi.batch',
            'res_id': batch.id,
            'view_mode': 'form',
            'target': 'current',
        }
