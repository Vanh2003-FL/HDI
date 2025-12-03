# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockQuant(models.Model):
    """
    ✅ INHERIT stock.quant (Odoo core)
    
    KHÔNG thay đổi logic tồn kho
    CHỈ thêm:
    - batch_id (link batch với quant)
    - Không sửa UI nhiều (chỉ thêm trường ẩn)
    
    ✅ Đây là TÂM ĐIỂM tồn kho - KHÔNG được fork logic
    """
    _inherit = 'stock.quant'
    
    # ===== BATCH LINK =====
    batch_id = fields.Many2one(
        'hdi.batch',
        string='Batch/LPN',
        index=True,
        help="Batch containing this inventory quant"
    )
    
    is_batched = fields.Boolean(
        compute='_compute_is_batched',
        store=True,
        string='Is Batched',
    )
    
    @api.depends('batch_id')
    def _compute_is_batched(self):
        """Check if quant is part of a batch"""
        for quant in self:
            quant.is_batched = bool(quant.batch_id)
    
    def write(self, vals):
        """
        ✅ OVERRIDE write nhưng GỌI super() - giữ 100% core logic
        Chỉ thêm batch sync khi location thay đổi
        """
        result = super().write(vals)
        
        # If location changed, update batch location
        if 'location_id' in vals:
            for quant in self:
                if quant.batch_id and quant.batch_id.location_id != quant.location_id:
                    # Sync batch location with quant location
                    quant.batch_id.location_id = quant.location_id
        
        # Recompute batch quantities if quantity changed
        if 'quantity' in vals or 'reserved_quantity' in vals:
            batches = self.mapped('batch_id').filtered(lambda b: b)
            batches._compute_quantities()
        
        return result
