# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PutawaySuggestion(models.Model):
    _name = 'putaway.suggestion'
    _description = 'Smart Putaway Suggestion Engine'
    _order = 'score desc, distance_score desc'

    name = fields.Char(string='Suggestion Reference', compute='_compute_name', store=True)
    
    # Input parameters
    product_id = fields.Many2one('product.product', string='Product', required=True)
    quantity = fields.Float(string='Quantity', required=True, digits='Product Unit of Measure')
    warehouse_id = fields.Many2one('wms.warehouse', string='Warehouse', required=True)
    
    # Suggestion rule
    rule = fields.Selection([
        ('abc_classification', 'ABC Classification Matching'),
        ('fifo', 'FIFO - Same Product Area'),
        ('fefo', 'FEFO - Same Expiry Area'),
        ('distance', 'Shortest Distance'),
        ('capacity', 'Best Fit Capacity'),
        ('mixed', 'Mixed Strategy (Recommended)'),
    ], string='Suggestion Rule', default='mixed', required=True)
    
    # Suggested location
    suggested_location_id = fields.Many2one('wms.location', string='Suggested Location')
    
    # Scoring
    score = fields.Float(string='Overall Score', digits=(10, 2),
                        help='Overall suitability score (0-100)')
    capacity_score = fields.Float(string='Capacity Score', digits=(10, 2))
    abc_score = fields.Float(string='ABC Score', digits=(10, 2))
    distance_score = fields.Float(string='Distance Score', digits=(10, 2))
    priority_score = fields.Float(string='Priority Score', digits=(10, 2))
    
    # Location details (for display)
    location_address = fields.Char(related='suggested_location_id.location_address', string='3D Address')
    available_capacity = fields.Float(related='suggested_location_id.available_capacity', string='Available Capacity')
    capacity_percentage = fields.Float(related='suggested_location_id.capacity_percentage', string='Capacity %')
    
    # Alternative suggestions
    rank = fields.Integer(string='Rank', default=1, help='1 = best, 2 = second best, etc.')
    
    @api.depends('product_id', 'suggested_location_id', 'score')
    def _compute_name(self):
        for record in self:
            if record.product_id and record.suggested_location_id:
                record.name = f'{record.product_id.name} → {record.suggested_location_id.complete_name} (Score: {record.score:.1f})'
            else:
                record.name = 'New Suggestion'

    @api.model
    def generate_suggestions(self, product_id, quantity, warehouse_id, rule='mixed', max_suggestions=5):
        """Generate putaway suggestions based on rule"""
        
        product = self.env['product.product'].browse(product_id)
        warehouse = self.env['wms.warehouse'].browse(warehouse_id)
        
        if not product or not warehouse:
            raise UserError(_('Invalid product or warehouse!'))
        
        # Base domain: storage locations with available capacity
        domain = [
            ('zone_id.warehouse_id', '=', warehouse_id),
            ('zone_id.zone_type', '=', 'storage'),
            ('location_status', '=', 'available'),
            ('available_capacity', '>=', quantity),
        ]
        
        # Add product-specific filters
        if product.wms_storage_type:
            domain.append(('storage_category', '=', product.wms_storage_type))
        
        if product.wms_hazardous:
            domain.append(('storage_category', '=', 'hazardous'))
        
        locations = self.env['wms.location'].search(domain)
        
        if not locations:
            raise UserError(_('No suitable locations found for this product!'))
        
        # Calculate scores based on rule
        suggestions = []
        
        for location in locations:
            if rule == 'abc_classification':
                score_data = self._score_abc(location, product, quantity)
            elif rule == 'fifo':
                score_data = self._score_fifo(location, product, quantity)
            elif rule == 'fefo':
                score_data = self._score_fefo(location, product, quantity)
            elif rule == 'distance':
                score_data = self._score_distance(location, product, quantity)
            elif rule == 'capacity':
                score_data = self._score_capacity(location, product, quantity)
            else:  # mixed
                score_data = self._score_mixed(location, product, quantity)
            
            suggestions.append({
                'product_id': product_id,
                'quantity': quantity,
                'warehouse_id': warehouse_id,
                'rule': rule,
                'suggested_location_id': location.id,
                'score': score_data['overall'],
                'capacity_score': score_data['capacity'],
                'abc_score': score_data['abc'],
                'distance_score': score_data['distance'],
                'priority_score': score_data['priority'],
            })
        
        # Sort by score and take top N
        suggestions.sort(key=lambda x: x['score'], reverse=True)
        top_suggestions = suggestions[:max_suggestions]
        
        # Assign ranks
        for idx, sugg in enumerate(top_suggestions, start=1):
            sugg['rank'] = idx
        
        # Delete old suggestions for this product
        self.search([
            ('product_id', '=', product_id),
            ('warehouse_id', '=', warehouse_id)
        ]).unlink()
        
        # Create suggestion records
        created_suggestions = self.env['putaway.suggestion']
        for sugg_data in top_suggestions:
            created_suggestions |= self.create(sugg_data)
        
        return created_suggestions

    def _score_abc(self, location, product, quantity):
        """Score based on ABC classification matching"""
        score = {'overall': 0, 'capacity': 0, 'abc': 0, 'distance': 0, 'priority': 0}
        
        # ABC match (0-50 points)
        if product.abc_classification and location.abc_zone:
            if product.abc_classification == location.abc_zone:
                score['abc'] = 50
            elif abs(ord(product.abc_classification) - ord(location.abc_zone)) == 1:
                score['abc'] = 25
        
        # Capacity (0-30 points)
        if location.capacity > 0:
            capacity_ratio = min(location.available_capacity / quantity, 1.0)
            score['capacity'] = capacity_ratio * 30
        
        # Distance from picking (0-20 points)
        if location.distance_from_picking > 0:
            score['distance'] = max(0, 20 - location.distance_from_picking)
        
        score['overall'] = sum(score.values())
        return score

    def _score_fifo(self, location, product, quantity):
        """Score for FIFO - prefer locations with same product"""
        score = {'overall': 0, 'capacity': 0, 'abc': 0, 'distance': 0, 'priority': 0}
        
        # Check if product already in location (0-50 points)
        quants = self.env['wms.stock.quant'].search([
            ('location_id', '=', location.id),
            ('product_id', '=', product.id),
            ('quantity', '>', 0)
        ])
        
        if quants:
            score['abc'] = 50  # Reuse abc field for FIFO scoring
        
        # Rest similar to ABC
        if location.capacity > 0:
            capacity_ratio = min(location.available_capacity / quantity, 1.0)
            score['capacity'] = capacity_ratio * 30
        
        score['distance'] = max(0, 20 - location.distance_from_receiving)
        score['overall'] = sum(score.values())
        return score

    def _score_fefo(self, location, product, quantity):
        """Score for FEFO - prefer locations with similar expiry products"""
        # Similar to FIFO but consider expiry dates
        return self._score_fifo(location, product, quantity)

    def _score_distance(self, location, product, quantity):
        """Score based on shortest distance"""
        score = {'overall': 0, 'capacity': 0, 'abc': 0, 'distance': 0, 'priority': 0}
        
        # Distance is primary factor (0-70 points)
        if location.distance_from_receiving > 0:
            score['distance'] = max(0, 70 - (location.distance_from_receiving * 2))
        else:
            score['distance'] = 70
        
        # Capacity (0-30 points)
        if location.capacity > 0:
            capacity_ratio = min(location.available_capacity / quantity, 1.0)
            score['capacity'] = capacity_ratio * 30
        
        score['overall'] = sum(score.values())
        return score

    def _score_capacity(self, location, product, quantity):
        """Score based on best fit capacity"""
        score = {'overall': 0, 'capacity': 0, 'abc': 0, 'distance': 0, 'priority': 0}
        
        # Best fit = available capacity close to quantity (0-70 points)
        if location.available_capacity > 0:
            fit_ratio = quantity / location.available_capacity
            if 0.8 <= fit_ratio <= 1.0:
                score['capacity'] = 70  # Perfect fit
            elif 0.5 <= fit_ratio < 0.8:
                score['capacity'] = 50
            else:
                score['capacity'] = 30
        
        # Priority (0-30 points)
        score['priority'] = (location.putaway_priority / 100) * 30
        
        score['overall'] = sum(score.values())
        return score

    def _score_mixed(self, location, product, quantity):
        """Mixed strategy combining all factors"""
        return {
            'overall': location.get_putaway_score(product, quantity),
            'capacity': (location.available_capacity / location.capacity * 40) if location.capacity > 0 else 0,
            'abc': 30 if (product.abc_classification == location.abc_zone) else 0,
            'distance': max(0, 20 - location.distance_from_picking),
            'priority': (location.putaway_priority / 100) * 10,
        }

    def action_apply_suggestion(self):
        """Apply this suggestion to related receipt/operation"""
        self.ensure_one()
        # This would be called from receipt wizard
        return {
            'type': 'ir.actions.act_window_close',
            'infos': {
                'location_id': self.suggested_location_id.id,
                'score': self.score,
            }
        }
