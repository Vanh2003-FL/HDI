# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class OddItemMergeWizard(models.TransientModel):
    _name = 'odd.item.merge.wizard'
    _description = 'Merge Odd Items Wizard'

    product_id = fields.Many2one('product.product', string='Product', required=True)
    warehouse_id = fields.Many2one('wms.warehouse', string='Warehouse', required=True)
    
    odd_item_ids = fields.Many2many('stock.odd.item', string='Odd Items to Merge',
                                   domain="[('product_id', '=', product_id), ('state', 'in', ['identified', 'stored'])]")
    total_quantity = fields.Float(string='Total Quantity', compute='_compute_total', digits='Product Unit of Measure')
    standard_pack_qty = fields.Float(related='product_id.standard_pack_qty')
    
    can_create_standard = fields.Boolean(string='Can Create Standard Pack',
                                        compute='_compute_can_create_standard')
    target_location_id = fields.Many2one('wms.location', string='Target Location', required=True)

    @api.depends('odd_item_ids.quantity')
    def _compute_total(self):
        for wizard in self:
            wizard.total_quantity = sum(wizard.odd_item_ids.mapped('quantity'))

    @api.depends('total_quantity', 'standard_pack_qty')
    def _compute_can_create_standard(self):
        for wizard in self:
            wizard.can_create_standard = wizard.total_quantity >= wizard.standard_pack_qty

    def action_merge(self):
        """Merge selected odd items"""
        self.ensure_one()
        
        if len(self.odd_item_ids) < 2:
            raise UserError(_('Please select at least 2 odd items to merge!'))
        
        # Mark all as merged
        self.odd_item_ids.write({'state': 'merged'})
        
        # Create batch merge operation if needed
        if self.env['ir.module.module'].search([('name', '=', 'hdi_stock_batch_flow'), ('state', '=', 'installed')]):
            # Integration with batch merge
            pass
        
        return {'type': 'ir.actions.act_window_close'}
