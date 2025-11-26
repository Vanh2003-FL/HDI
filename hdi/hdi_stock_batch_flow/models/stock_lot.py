# -*- coding: utf-8 -*-
from odoo import models, fields, api


class StockLot(models.Model):
    _inherit = 'stock.lot'

    # Batch flow tracking
    split_from_id = fields.Many2one('stock.lot', string='Split From Batch', readonly=True,
                                   help='Parent batch if this was created from split')
    split_ids = fields.One2many('stock.batch.split.line', 'new_lot_id', string='Split Operations')
    split_count = fields.Integer(string='Splits', compute='_compute_split_count')
    
    merge_source_ids = fields.One2many('stock.batch.merge.line', 'source_batch_id',
                                      string='Merge Operations (as Source)')
    merge_target_ids = fields.Many2many('stock.batch.merge', string='Merge Operations (as Target)',
                                       compute='_compute_merge_operations')
    merge_count = fields.Integer(string='Merges', compute='_compute_merge_count')
    
    # QR code for tracking
    qr_code = fields.Binary(string='QR Code', attachment=True)

    @api.depends('split_ids')
    def _compute_split_count(self):
        for record in self:
            record.split_count = len(record.split_ids)

    def _compute_merge_operations(self):
        for record in self:
            merges = self.env['stock.batch.merge'].search([
                ('target_batch_id', '=', record.id)
            ])
            record.merge_target_ids = merges

    @api.depends('merge_source_ids', 'merge_target_ids')
    def _compute_merge_count(self):
        for record in self:
            record.merge_count = len(record.merge_source_ids) + len(record.merge_target_ids)

    def action_view_split_operations(self):
        """View split operations for this batch"""
        self.ensure_one()
        return {
            'name': _('Split Operations'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.batch.split',
            'view_mode': 'list,form',
            'domain': ['|', ('parent_batch_id', '=', self.id),
                      ('child_batch_ids.new_lot_id', '=', self.id)],
            'context': {'create': False}
        }

    def action_view_merge_operations(self):
        """View merge operations for this batch"""
        self.ensure_one()
        return {
            'name': _('Merge Operations'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.batch.merge',
            'view_mode': 'list,form',
            'domain': ['|', ('source_batch_ids.source_batch_id', '=', self.id),
                      ('target_batch_id', '=', self.id)],
            'context': {'create': False}
        }
