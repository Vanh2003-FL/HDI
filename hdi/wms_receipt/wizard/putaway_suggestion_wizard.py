# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PutawaySuggestionWizard(models.TransientModel):
    _name = 'putaway.suggestion.wizard'
    _description = 'Putaway Suggestion Wizard'

    receipt_id = fields.Many2one('wms.receipt', string='Receipt', required=True)
    strategy = fields.Selection([
        ('nearest', 'Nearest Available'),
        ('fifo', 'FIFO Location'),
        ('fefo', 'FEFO Location'),
        ('fixed', 'Fixed Location'),
    ], string='Strategy', default='nearest', required=True)
    
    line_ids = fields.One2many('putaway.suggestion.line', 'wizard_id', string='Suggestions')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        
        if 'receipt_id' in res and res['receipt_id']:
            receipt = self.env['wms.receipt'].browse(res['receipt_id'])
            
            # Generate suggestions for each line
            suggestions = []
            for line in receipt.line_ids.filtered(lambda l: l.received_qty > 0):
                location = receipt._get_putaway_location(line)
                
                if location:
                    suggestions.append((0, 0, {
                        'receipt_line_id': line.id,
                        'product_id': line.product_id.id,
                        'quantity': line.received_qty,
                        'suggested_location_id': location.id,
                        'capacity_percentage': location.capacity_percentage,
                    }))
            
            res['line_ids'] = suggestions
        
        return res

    def action_confirm(self):
        """Apply suggested locations"""
        self.ensure_one()
        
        for line in self.line_ids:
            if line.selected and line.suggested_location_id:
                line.receipt_line_id.write({
                    'putaway_location_id': line.suggested_location_id.id
                })
        
        # Create putaway moves
        self.receipt_id.action_create_putaway_moves()
        
        return {'type': 'ir.actions.act_window_close'}


class PutawaySuggestionLine(models.TransientModel):
    _name = 'putaway.suggestion.line'
    _description = 'Putaway Suggestion Line'
    _order = 'sequence'

    sequence = fields.Integer(string='Sequence', default=10)
    wizard_id = fields.Many2one('putaway.suggestion.wizard', string='Wizard', required=True,
                               ondelete='cascade')
    
    receipt_line_id = fields.Many2one('wms.receipt.line', string='Receipt Line', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    quantity = fields.Float(string='Quantity', digits='Product Unit of Measure')
    
    suggested_location_id = fields.Many2one('wms.location', string='Suggested Location',
                                           domain="[('zone_id.zone_type', '=', 'storage'), ('location_status', '=', 'available')]")
    capacity_percentage = fields.Float(string='Capacity %')
    
    selected = fields.Boolean(string='Select', default=True)
    
    # Alternative locations
    alternative_location_ids = fields.Many2many('wms.location', string='Alternative Locations',
                                               compute='_compute_alternatives')

    @api.depends('product_id', 'suggested_location_id')
    def _compute_alternatives(self):
        """Suggest 3 alternative locations"""
        for record in self:
            if record.product_id and record.suggested_location_id:
                alternatives = self.env['wms.location'].search([
                    ('zone_id.zone_type', '=', 'storage'),
                    ('location_status', '=', 'available'),
                    ('available_capacity', '>', 0),
                    ('id', '!=', record.suggested_location_id.id),
                ], limit=3, order='capacity_percentage')
                
                record.alternative_location_ids = alternatives
            else:
                record.alternative_location_ids = False
