# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PutawayWizard(models.TransientModel):
    _name = 'hdi.putaway.wizard'
    _description = 'Putaway Location Wizard'
    
    batch_id = fields.Many2one(
        'hdi.batch',
        string='Batch',
        default=lambda self: self.env.context.get('default_batch_id'),
    )
    
    picking_id = fields.Many2one(
        'stock.picking',
        string='Picking',
        default=lambda self: self.env.context.get('default_picking_id'),
    )
    
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
    )
    
    quantity = fields.Float(
        string='Quantity',
        required=True,
    )
    
    suggestion_ids = fields.Many2many(
        'hdi.putaway.suggestion',
        string='Suggestions',
        compute='_compute_suggestions',
    )
    
    selected_location_id = fields.Many2one(
        'stock.location',
        string='Selected Location',
    )
    
    @api.depends('batch_id', 'product_id', 'quantity')
    def _compute_suggestions(self):
        """Generate putaway suggestions"""
        for wizard in self:
            if wizard.batch_id and wizard.product_id:
                # Clear old suggestions
                wizard.batch_id.mapped('putaway_suggestion_ids').unlink()
                
                # Generate new suggestions
                suggestions = self.env['hdi.putaway.suggestion'].generate_suggestions(
                    wizard.batch_id,
                    max_suggestions=5
                )
                wizard.suggestion_ids = suggestions
            else:
                wizard.suggestion_ids = False
    
    def action_generate_suggestions(self):
        """Manually trigger suggestion generation"""
        self.ensure_one()
        self._compute_suggestions()
        return {'type': 'ir.actions.do_nothing'}
    
    def action_confirm_location(self):
        """Confirm selected location and update batch"""
        self.ensure_one()
        
        if not self.selected_location_id:
            raise UserError(_('Please select a location first.'))
        
        # Update batch
        self.batch_id.write({
            'location_dest_id': self.selected_location_id.id,
        })
        
        # Update picking WMS state
        if self.picking_id:
            self.picking_id.wms_state = 'putaway_pending'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Location Set'),
                'message': _('Putaway location set to %s') % self.selected_location_id.complete_name,
                'type': 'success',
                'sticky': False,
            }
        }
