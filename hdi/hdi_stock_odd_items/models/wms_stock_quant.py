# -*- coding: utf-8 -*-
from odoo import models, fields, api


class WmsStockQuant(models.Model):
    _inherit = 'wms.stock.quant'

    # Odd item tracking
    is_odd = fields.Boolean(string='Is Odd Item', default=False, index=True,
                           help='Mark if this stock is an odd/remnant item (less than standard pack)')
    odd_item_id = fields.Many2one('stock.odd.item', string='Odd Item Reference', readonly=True,
                                  help='Link to odd item management record')
    
    # Override/extend to auto-detect odd items
    @api.model
    def create(self, vals):
        quant = super().create(vals)
        quant._check_if_odd()
        return quant
    
    def write(self, vals):
        res = super().write(vals)
        if 'quantity' in vals:
            self._check_if_odd()
        return res
    
    def _check_if_odd(self):
        """Auto-check if quant quantity is odd"""
        for quant in self:
            if quant.product_id.standard_pack_qty > 0:
                should_be_odd = quant.quantity < quant.product_id.standard_pack_qty and quant.quantity > 0
                if should_be_odd != quant.is_odd:
                    quant.write({'is_odd': should_be_odd})
