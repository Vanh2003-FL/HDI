# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class BatchMergeWizard(models.TransientModel):
    _name = 'batch.merge.wizard'
    _description = 'Quick Batch Merge Wizard'

    product_id = fields.Many2one('product.product', string='Product', required=True,
                                domain=[('type', '=', 'product')])
    warehouse_id = fields.Many2one('wms.warehouse', string='Warehouse', required=True)
    location_id = fields.Many2one('wms.location', string='Location', required=True)
    
    # Source batches selection
    source_batch_ids = fields.Many2many('stock.lot', string='Batches to Merge',
                                       domain="[('product_id', '=', product_id)]")
    
    # Target
    create_new_target = fields.Boolean(string='Create New Target', default=True)
    new_target_name = fields.Char(string='New Target Name')
    target_batch_id = fields.Many2one('stock.lot', string='Existing Target',
                                     domain="[('product_id', '=', product_id)]")
    
    reason = fields.Text(string='Reason')

    @api.onchange('create_new_target')
    def _onchange_create_new(self):
        if self.create_new_target:
            self.target_batch_id = False
            if not self.new_target_name:
                self.new_target_name = f'MERGED-{fields.Date.today()}'

    def action_create_merge(self):
        """Create batch merge operation"""
        self.ensure_one()
        
        if len(self.source_batch_ids) < 2:
            raise UserError(_('Must select at least 2 batches to merge!'))
        
        # Create merge operation
        merge_vals = {
            'product_id': self.product_id.id,
            'warehouse_id': self.warehouse_id.id,
            'location_id': self.location_id.id,
            'reason': self.reason,
            'merge_type': 'remnants',
            'create_new_target': self.create_new_target,
        }
        
        if self.create_new_target:
            merge_vals['new_target_name'] = self.new_target_name
        else:
            merge_vals['target_batch_id'] = self.target_batch_id.id
        
        merge = self.env['stock.batch.merge'].create(merge_vals)
        
        # Create source lines
        for lot in self.source_batch_ids:
            quants = self.env['wms.stock.quant'].search([
                ('lot_id', '=', lot.id),
                ('location_id', '=', self.location_id.id),
                ('status', '=', 'available'),
            ])
            available_qty = sum(quants.mapped('available_quantity'))
            
            if available_qty > 0:
                self.env['stock.batch.merge.line'].create({
                    'merge_id': merge.id,
                    'source_batch_id': lot.id,
                    'quantity': available_qty,
                    'available_quantity': available_qty,
                })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.batch.merge',
            'res_id': merge.id,
            'view_mode': 'form',
            'target': 'current',
        }
