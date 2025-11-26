from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PutawaySuggestion(models.Model):
    _name = 'putaway.suggestion'
    _description = 'Putaway Suggestion Engine'
    _order = 'priority desc, id'

    name = fields.Char(
        string='Rule Name',
        required=True
    )
    active = fields.Boolean(
        string='Active',
        default=True
    )
    priority = fields.Integer(
        string='Priority',
        default=10,
        help='Higher priority rules are evaluated first'
    )
    
    # Conditions
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        help='Leave empty to apply to all products'
    )
    product_categ_id = fields.Many2one(
        'product.category',
        string='Product Category',
        help='Leave empty to apply to all categories'
    )
    
    # Strategy
    strategy = fields.Selection([
        ('fifo', 'FIFO - First In First Out'),
        ('lifo', 'LIFO - Last In First Out'),
        ('fefo', 'FEFO - First Expired First Out'),
        ('abc', 'ABC Classification'),
        ('nearest', 'Nearest to Dock'),
        ('capacity', 'Available Capacity'),
        ('fixed', 'Fixed Location'),
    ], string='Strategy', required=True, default='fifo')
    
    # ABC Settings
    abc_class = fields.Selection([
        ('a', 'A - High Turnover'),
        ('b', 'B - Medium Turnover'),
        ('c', 'C - Low Turnover'),
    ], string='ABC Class')
    
    # Fixed Location
    fixed_location_id = fields.Many2one(
        'stock.location',
        string='Fixed Location',
        domain=[('usage', '=', 'internal')]
    )
    
    # Warehouse
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
        help='Leave empty to apply to all warehouses'
    )
    
    # Constraints
    min_accessibility = fields.Integer(
        string='Min Accessibility Score',
        help='Minimum accessibility score required'
    )
    max_distance = fields.Float(
        string='Max Distance from Dock (m)',
        help='Maximum distance from dock'
    )
    require_same_product = fields.Boolean(
        string='Group Same Products',
        help='Suggest locations already containing the same product'
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )

    def suggest_location(self, product, quantity, warehouse=None):
        """
        Main method to suggest a putaway location
        Returns: stock.location record
        """
        self.ensure_one()
        
        domain = [
            ('usage', '=', 'internal'),
            ('is_blocked', '=', False),
        ]
        
        if warehouse:
            domain.append(('warehouse_id', '=', warehouse.id))
        elif self.warehouse_id:
            domain.append(('warehouse_id', '=', self.warehouse_id.id))
        
        if self.min_accessibility:
            domain.append(('accessibility_score', '>=', self.min_accessibility))
        
        if self.max_distance:
            domain.append(('distance_from_dock', '<=', self.max_distance))
        
        locations = self.env['stock.location'].search(domain)
        
        if not locations:
            return self.env['stock.location']
        
        # Apply strategy
        if self.strategy == 'fixed' and self.fixed_location_id:
            return self.fixed_location_id
        
        elif self.strategy == 'abc' and self.abc_class:
            locations = locations.filtered(lambda l: l.abc_classification == self.abc_class)
        
        elif self.strategy == 'nearest':
            locations = locations.sorted('distance_from_dock')
        
        elif self.strategy == 'capacity':
            # Filter locations with enough capacity
            suitable_locations = self.env['stock.location']
            product_volume = product.volume or 0.0
            required_volume = product_volume * quantity
            
            for loc in locations:
                available = loc.get_available_capacity()
                if available >= required_volume:
                    suitable_locations |= loc
            
            locations = suitable_locations
        
        elif self.strategy in ['fifo', 'fefo']:
            # Suggest locations with same product first (FIFO)
            if self.require_same_product:
                locations_with_product = self.env['stock.location']
                for loc in locations:
                    quant = self.env['stock.quant'].search([
                        ('location_id', '=', loc.id),
                        ('product_id', '=', product.id),
                        ('quantity', '>', 0)
                    ], limit=1)
                    if quant:
                        locations_with_product |= loc
                
                if locations_with_product:
                    locations = locations_with_product
        
        # Return first suitable location
        return locations[:1] if locations else self.env['stock.location']

    @api.model
    def get_suggested_location(self, product_id, quantity, warehouse_id=None):
        """
        Public method to get location suggestion
        """
        product = self.env['product.product'].browse(product_id)
        warehouse = self.env['stock.warehouse'].browse(warehouse_id) if warehouse_id else None
        
        # Find applicable rules
        domain = [
            ('active', '=', True),
            '|', ('product_id', '=', False), ('product_id', '=', product_id),
            '|', ('product_categ_id', '=', False), ('product_categ_id', '=', product.categ_id.id),
        ]
        
        if warehouse_id:
            domain = ['|', ('warehouse_id', '=', False), ('warehouse_id', '=', warehouse_id)] + domain
        
        rules = self.search(domain, order='priority desc, id')
        
        # Try each rule until we find a suitable location
        for rule in rules:
            location = rule.suggest_location(product, quantity, warehouse)
            if location:
                return location
        
        # No suitable location found
        return self.env['stock.location']


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    location_full_name = fields.Char(
        related='location_id.location_full_name',
        string='Full Location',
        readonly=True
    )
