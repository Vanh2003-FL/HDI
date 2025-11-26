# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ProductProduct(models.Model):
    _inherit = 'product.product'

    # Standard pack quantity
    standard_pack_qty = fields.Float(string='Standard Pack Qty', default=1.0,
                                    help='Standard quantity per pallet/case/pack. '
                                         'Quantities below this are considered odd items.')
    
    # Odd item statistics
    odd_item_count = fields.Integer(string='Odd Items', compute='_compute_odd_items')
    total_odd_quantity = fields.Float(string='Total Odd Qty', compute='_compute_odd_items',
                                     digits='Product Unit of Measure')

    @api.depends('id')
    def _compute_odd_items(self):
        for product in self:
            odd_items = self.env['stock.odd.item'].search([
                ('product_id', '=', product.id),
                ('state', 'in', ['identified', 'stored']),
            ])
            product.odd_item_count = len(odd_items)
            product.total_odd_quantity = sum(odd_items.mapped('quantity'))

    def action_view_odd_items(self):
        """View odd items for this product"""
        self.ensure_one()
        return {
            'name': _('Odd Items - %s') % self.display_name,
            'type': 'ir.actions.act_window',
            'res_model': 'stock.odd.item',
            'view_mode': 'list,form',
            'domain': [('product_id', '=', self.id)],
            'context': {'default_product_id': self.id}
        }


class WmsLocation(models.Model):
    _inherit = 'wms.location'

    is_odd_item_location = fields.Boolean(string='Odd Item Location', default=False,
                                         help='Designate this location for storing odd/remnant items')
    odd_item_count = fields.Integer(string='Odd Items', compute='_compute_odd_items')

    @api.depends('id')
    def _compute_odd_items(self):
        for location in self:
            location.odd_item_count = self.env['stock.odd.item'].search_count([
                ('location_id', '=', location.id),
                ('state', 'in', ['identified', 'stored']),
            ])
