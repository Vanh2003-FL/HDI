# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class SmartPutawayWizard(models.TransientModel):
    _name = 'smart.putaway.wizard'
    _description = 'Smart Putaway Suggestion Wizard'

    product_id = fields.Many2one('product.product', string='Product', required=True)
    quantity = fields.Float(string='Quantity', required=True, digits='Product Unit of Measure')
    warehouse_id = fields.Many2one('wms.warehouse', string='Warehouse', required=True)
    
    rule = fields.Selection([
        ('abc_classification', 'ABC Classification Matching'),
        ('fifo', 'FIFO - Same Product Area'),
        ('fefo', 'FEFO - Same Expiry Area'),
        ('distance', 'Shortest Distance'),
        ('capacity', 'Best Fit Capacity'),
        ('mixed', 'Mixed Strategy (Recommended)'),
    ], string='Suggestion Rule', default='mixed', required=True)
    
    max_suggestions = fields.Integer(string='Max Suggestions', default=5, required=True)
    
    # Suggested locations
    suggestion_ids = fields.One2many('putaway.suggestion', 'wizard_id', string='Suggestions')
    selected_location_id = fields.Many2one('wms.location', string='Selected Location')
    
    def action_generate_suggestions(self):
        """Generate putaway suggestions"""
        self.ensure_one()
        
        # Clear previous suggestions
        self.suggestion_ids.unlink()
        
        # Generate new suggestions
        suggestions = self.env['putaway.suggestion'].generate_suggestions(
            product_id=self.product_id.id,
            quantity=self.quantity,
            warehouse_id=self.warehouse_id.id,
            rule=self.rule,
            max_suggestions=self.max_suggestions
        )
        
        # Link to wizard
        suggestions.write({'wizard_id': self.id})
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'smart.putaway.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
    
    def action_apply_suggestion(self):
        """Apply selected suggestion"""
        self.ensure_one()
        
        if not self.selected_location_id:
            raise UserError(_('Please select a location first!'))
        
        return {
            'type': 'ir.actions.act_window_close',
            'infos': {
                'location_id': self.selected_location_id.id,
            }
        }


class PutawaySuggestion(models.Model):
    _inherit = 'putaway.suggestion'
    
    wizard_id = fields.Many2one('smart.putaway.wizard', string='Wizard', ondelete='cascade')
