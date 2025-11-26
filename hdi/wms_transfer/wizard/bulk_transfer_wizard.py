# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class BulkTransferWizard(models.TransientModel):
    _name = 'bulk.transfer.wizard'
    _description = 'Bulk Transfer Wizard'

    warehouse_id = fields.Many2one(
        'wms.warehouse',
        string='Warehouse',
        required=True
    )
    
    source_location_id = fields.Many2one(
        'wms.location',
        string='Source Location',
        required=True,
        domain="[('warehouse_id', '=', warehouse_id)]"
    )
    
    dest_location_id = fields.Many2one(
        'wms.location',
        string='Destination Location',
        required=True,
        domain="[('warehouse_id', '=', warehouse_id), ('id', '!=', source_location_id)]"
    )
    
    transfer_type = fields.Selection([
        ('replenishment', 'Replenishment'),
        ('reorganization', 'Reorganization'),
        ('consolidation', 'Consolidation'),
        ('damage', 'Damaged Goods'),
        ('quarantine', 'To Quarantine'),
        ('return', 'Return to Storage'),
        ('other', 'Other')
    ], string='Transfer Type', required=True, default='replenishment')
    
    reason = fields.Text(
        string='Reason'
    )
    
    transfer_all_stock = fields.Boolean(
        string='Transfer All Stock',
        help='Transfer all available stock from source location'
    )
    
    product_ids = fields.Many2many(
        'product.product',
        string='Products',
        domain=[('type', '=', 'product')],
        help='Leave empty to transfer all products'
    )

    def action_create_transfer(self):
        """Create transfer with all products from source location"""
        self.ensure_one()
        
        # Get stock from source location
        quant_obj = self.env['wms.stock.quant']
        domain = [
            ('location_id', '=', self.source_location_id.id),
            ('status', '=', 'available'),
            ('available_quantity', '>', 0)
        ]
        
        if not self.transfer_all_stock and self.product_ids:
            domain.append(('product_id', 'in', self.product_ids.ids))
        
        quants = quant_obj.search(domain)
        
        if not quants:
            raise UserError(_('No available stock found in source location.'))
        
        # Create transfer
        transfer_vals = {
            'warehouse_id': self.warehouse_id.id,
            'source_location_id': self.source_location_id.id,
            'dest_location_id': self.dest_location_id.id,
            'transfer_type': self.transfer_type,
            'reason': self.reason,
        }
        transfer = self.env['wms.transfer'].create(transfer_vals)
        
        # Create lines from quants
        for quant in quants:
            line_vals = {
                'transfer_id': transfer.id,
                'product_id': quant.product_id.id,
                'lot_id': quant.lot_id.id if quant.lot_id else False,
                'quantity': quant.available_quantity,
                'quantity_done': 0.0,
            }
            self.env['wms.transfer.line'].create(line_vals)
        
        # Return action to view created transfer
        return {
            'type': 'ir.actions.act_window',
            'name': _('Internal Transfer'),
            'res_model': 'wms.transfer',
            'res_id': transfer.id,
            'view_mode': 'form',
            'target': 'current',
        }
