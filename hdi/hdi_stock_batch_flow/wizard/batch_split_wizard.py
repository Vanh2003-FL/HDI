# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class BatchSplitWizard(models.TransientModel):
    _name = 'batch.split.wizard'
    _description = 'Quick Batch Split Wizard'

    parent_batch_id = fields.Many2one('stock.lot', string='Batch to Split', required=True,
                                     domain=[('product_id', '!=', False)])
    product_id = fields.Many2one(related='parent_batch_id.product_id', string='Product')
    available_quantity = fields.Float(string='Available Quantity', digits='Product Unit of Measure')
    
    warehouse_id = fields.Many2one('wms.warehouse', string='Warehouse', required=True)
    location_id = fields.Many2one('wms.location', string='Location', required=True)
    
    # Quick split options
    split_method = fields.Selection([
        ('equal', 'Equal Parts'),
        ('custom', 'Custom Quantities'),
    ], string='Split Method', default='equal', required=True)
    
    num_parts = fields.Integer(string='Number of Parts', default=2,
                               help='Split into N equal parts')
    child_quantity = fields.Float(string='Quantity per Part', digits='Product Unit of Measure',
                                 compute='_compute_child_quantity', store=True, readonly=False)
    
    reason = fields.Text(string='Reason')

    @api.depends('split_method', 'num_parts', 'available_quantity')
    def _compute_child_quantity(self):
        for wizard in self:
            if wizard.split_method == 'equal' and wizard.num_parts > 0:
                wizard.child_quantity = wizard.available_quantity / wizard.num_parts
            else:
                wizard.child_quantity = 0.0

    @api.onchange('parent_batch_id', 'location_id')
    def _onchange_batch(self):
        if self.parent_batch_id and self.location_id:
            quants = self.env['wms.stock.quant'].search([
                ('lot_id', '=', self.parent_batch_id.id),
                ('location_id', '=', self.location_id.id),
                ('status', '=', 'available'),
            ])
            self.available_quantity = sum(quants.mapped('available_quantity'))

    def action_create_split(self):
        """Create batch split operation"""
        self.ensure_one()
        
        if self.num_parts < 2:
            raise UserError(_('Must split into at least 2 parts!'))
        
        # Create split operation
        split = self.env['stock.batch.split'].create({
            'parent_batch_id': self.parent_batch_id.id,
            'warehouse_id': self.warehouse_id.id,
            'location_id': self.location_id.id,
            'reason': self.reason,
            'split_type': 'manual',
        })
        
        # Create child lines
        for i in range(self.num_parts):
            self.env['stock.batch.split.line'].create({
                'split_id': split.id,
                'new_lot_name': f'{self.parent_batch_id.name}-{i+1}',
                'quantity': self.child_quantity,
                'sequence': (i + 1) * 10,
            })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.batch.split',
            'res_id': split.id,
            'view_mode': 'form',
            'target': 'current',
        }
