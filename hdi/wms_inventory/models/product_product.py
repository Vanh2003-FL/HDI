# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ProductProduct(models.Model):
    _inherit = 'product.product'

    wms_qty_available = fields.Float(string='WMS Available Qty',
                                     compute='_compute_wms_quantities',
                                     digits='Product Unit of Measure')
    wms_qty_reserved = fields.Float(string='WMS Reserved Qty',
                                    compute='_compute_wms_quantities',
                                    digits='Product Unit of Measure')
    wms_qty_on_hand = fields.Float(string='WMS On Hand Qty',
                                   compute='_compute_wms_quantities',
                                   digits='Product Unit of Measure')
    
    wms_quant_ids = fields.One2many('wms.stock.quant', 'product_id', string='WMS Stock')

    def _compute_wms_quantities(self):
        for record in self:
            quants = record.wms_quant_ids.filtered(lambda q: q.status == 'available')
            record.wms_qty_on_hand = sum(quants.mapped('quantity'))
            record.wms_qty_reserved = sum(quants.mapped('reserved_quantity'))
            record.wms_qty_available = sum(quants.mapped('available_quantity'))

    def action_view_wms_stock(self):
        self.ensure_one()
        return {
            'name': _('WMS Stock'),
            'type': 'ir.actions.act_window',
            'res_model': 'wms.stock.quant',
            'view_mode': 'list,form',
            'domain': [('product_id', '=', self.id)],
            'context': {'default_product_id': self.id},
        }
