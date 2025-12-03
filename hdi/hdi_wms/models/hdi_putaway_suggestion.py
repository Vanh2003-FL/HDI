# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HdiPutawaySuggestion(models.Model):
    """
    ❌ Odoo core KHÔNG có putaway suggestion engine
    ✅ Phải tạo mới - Tính toán gợi ý vị trí tối ưu
    
    NHƯNG: Kết quả update vào stock.location (core)
    """
    _name = 'hdi.putaway.suggestion'
    _description = 'Putaway Location Suggestion'
    _order = 'priority, score desc'
    
    # ===== REFERENCE =====
    batch_id = fields.Many2one(
        'hdi.batch',
        string='Batch',
        required=True,
        ondelete='cascade',
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
    
    # ===== SUGGESTED LOCATION =====
    location_id = fields.Many2one(
        'stock.location',
        string='Suggested Location',
        required=True,
        domain="[('usage', '=', 'internal'), ('is_putable', '=', True)]"
    )
    
    location_display = fields.Char(
        related='location_id.complete_name',
        string='Location',
    )
    
    coordinates = fields.Char(
        related='location_id.coordinate_display',
        string='Coordinates',
    )
    
    # ===== SCORING =====
    score = fields.Float(
        string='Score',
        help="Calculated score (higher = better match)",
        digits=(16, 2),
    )
    
    priority = fields.Integer(
        related='location_id.location_priority',
        string='Priority',
        store=True,
    )
    
    # ===== CAPACITY CHECK =====
    available_capacity = fields.Float(
        compute='_compute_capacity_info',
        string='Available Capacity',
    )
    
    capacity_sufficient = fields.Boolean(
        compute='_compute_capacity_info',
        string='Capacity OK',
    )
    
    # ===== REASONS =====
    match_reasons = fields.Text(
        string='Match Reasons',
        help="Why this location was suggested"
    )
    
    warning_messages = fields.Text(
        string='Warnings',
        help="Potential issues with this location"
    )
    
    # ===== STATUS =====
    state = fields.Selection([
        ('suggested', 'Suggested'),
        ('selected', 'Selected'),
        ('rejected', 'Rejected'),
    ], string='State', default='suggested')
    
    @api.depends('location_id', 'product_id', 'quantity')
    def _compute_capacity_info(self):
        """Check if location has sufficient capacity"""
        for suggestion in self:
            if suggestion.location_id and suggestion.product_id:
                suggestion.capacity_sufficient = suggestion.location_id.get_available_capacity_for_product(
                    suggestion.product_id,
                    suggestion.quantity
                )
                suggestion.available_capacity = suggestion.location_id.available_volume
            else:
                suggestion.capacity_sufficient = False
                suggestion.available_capacity = 0.0
    
    @api.model
    def generate_suggestions(self, batch, max_suggestions=5):
        """
        ✅ ENGINE LOGIC: Tính toán gợi ý vị trí
        
        Tiêu chí:
        1. Capacity available
        2. Same product already there (consolidate)
        3. Moving class match (A with A, B with B)
        4. Distance optimization (closest to receiving)
        5. FIFO/FEFO rules
        """
        if not batch.product_id:
            raise UserError(_('Batch must have a product to suggest locations.'))
        
        product = batch.product_id
        quantity = batch.total_quantity or 0
        
        # Find suitable locations
        candidate_locations = self.env['stock.location'].search([
            ('usage', '=', 'internal'),
            ('is_putable', '=', True),
            ('company_id', '=', batch.company_id.id),
        ])
        
        suggestions = []
        for location in candidate_locations:
            # Skip if no capacity
            if not location.get_available_capacity_for_product(product, quantity):
                continue
            
            # Calculate score
            score = 0
            reasons = []
            warnings = []
            
            # 1. Same product exists (consolidation bonus)
            existing_quants = location.quant_ids.filtered(
                lambda q: q.product_id == product
            )
            if existing_quants:
                score += 50
                reasons.append('Same product already stored here (consolidation)')
            
            # 2. Moving class match
            if location.moving_class and hasattr(product, 'abc_classification'):
                if product.abc_classification == location.moving_class:
                    score += 30
                    reasons.append('Moving class matches')
                else:
                    score -= 10
                    warnings.append('Moving class mismatch')
            
            # 3. Priority
            score += (100 - location.location_priority)
            
            # 4. Empty location bonus
            if not location.quant_ids:
                score += 20
                reasons.append('Empty location')
            
            # 5. Temperature zone match
            if hasattr(product, 'storage_temperature') and product.storage_temperature == location.temperature_zone:
                score += 15
                reasons.append('Temperature zone matches')
            
            # 6. Capacity usage (prefer locations with good fit)
            if location.max_volume:
                required_volume = product.volume * quantity
                fit_ratio = required_volume / location.max_volume
                if 0.3 <= fit_ratio <= 0.8:  # Good fit
                    score += 10
                    reasons.append('Good capacity fit')
            
            suggestions.append({
                'batch_id': batch.id,
                'product_id': product.id,
                'quantity': quantity,
                'location_id': location.id,
                'score': score,
                'match_reasons': '\n'.join(reasons),
                'warning_messages': '\n'.join(warnings) if warnings else False,
                'state': 'suggested',
            })
        
        # Sort by score and limit
        suggestions = sorted(suggestions, key=lambda s: (-s['score'], s['location_id']))
        suggestions = suggestions[:max_suggestions]
        
        # Create suggestion records
        suggestion_records = self.env['hdi.putaway.suggestion'].create(suggestions)
        
        return suggestion_records
    
    def action_select(self):
        """
        Select this location for putaway
        ✅ Update batch.location_dest_id (which will update stock.location)
        """
        self.ensure_one()
        
        if not self.capacity_sufficient:
            raise UserError(_('Selected location does not have sufficient capacity.'))
        
        # Update batch destination
        self.batch_id.write({
            'location_dest_id': self.location_id.id,
        })
        
        # Mark this as selected, others as rejected
        self.state = 'selected'
        self.search([
            ('batch_id', '=', self.batch_id.id),
            ('id', '!=', self.id),
        ]).write({'state': 'rejected'})
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Location Selected'),
                'message': _('Putaway location set to %s') % self.location_id.complete_name,
                'type': 'success',
                'sticky': False,
            }
        }
