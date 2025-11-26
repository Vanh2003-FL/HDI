from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class StockLocation(models.Model):
    _inherit = 'stock.location'

    # 3D Coordinates
    coordinate_x = fields.Float(
        string='X Coordinate',
        help='Horizontal position (Aisle/Row)'
    )
    coordinate_y = fields.Float(
        string='Y Coordinate',
        help='Depth position (Bay/Column)'
    )
    coordinate_z = fields.Float(
        string='Z Coordinate',
        help='Height position (Level/Shelf)'
    )
    
    # Warehouse Structure
    floor_level = fields.Integer(
        string='Floor Level',
        help='Tầng trong kho'
    )
    aisle = fields.Char(
        string='Aisle',
        help='Dãy kho (A, B, C...)'
    )
    rack = fields.Char(
        string='Rack',
        help='Kệ trong dãy (01, 02, 03...)'
    )
    shelf = fields.Char(
        string='Shelf',
        help='Ô/Kệ cụ thể'
    )
    
    # Location Properties
    location_capacity = fields.Float(
        string='Capacity (m³)',
        help='Capacity in cubic meters'
    )
    max_weight = fields.Float(
        string='Max Weight (kg)',
        help='Maximum weight capacity'
    )
    location_type = fields.Selection([
        ('ground', 'Ground'),
        ('rack', 'Rack'),
        ('shelf', 'Shelf'),
        ('bin', 'Bin'),
        ('pallet', 'Pallet Position'),
    ], string='Location Type', default='rack')
    
    # ABC Classification
    abc_classification = fields.Selection([
        ('a', 'A - High Turnover'),
        ('b', 'B - Medium Turnover'),
        ('c', 'C - Low Turnover'),
    ], string='ABC Classification',
       help='Classification based on product movement frequency')
    
    # Accessibility
    accessibility_score = fields.Integer(
        string='Accessibility Score',
        help='Score from 1-100, higher is more accessible',
        default=50
    )
    distance_from_dock = fields.Float(
        string='Distance from Dock (m)',
        help='Distance from receiving/shipping dock'
    )
    
    # Status
    is_blocked = fields.Boolean(
        string='Blocked',
        help='Location is temporarily blocked'
    )
    blocked_reason = fields.Text(string='Block Reason')
    
    # Display name with coordinates
    location_full_name = fields.Char(
        string='Full Location',
        compute='_compute_location_full_name',
        store=True
    )

    @api.depends('name', 'floor_level', 'aisle', 'rack', 'shelf')
    def _compute_location_full_name(self):
        for location in self:
            parts = [location.name]
            if location.floor_level:
                parts.append(f'Floor:{location.floor_level}')
            if location.aisle:
                parts.append(f'Aisle:{location.aisle}')
            if location.rack:
                parts.append(f'Rack:{location.rack}')
            if location.shelf:
                parts.append(f'Shelf:{location.shelf}')
            location.location_full_name = ' / '.join(parts)

    @api.constrains('coordinate_x', 'coordinate_y', 'coordinate_z')
    def _check_coordinates(self):
        for location in self:
            if any([
                location.coordinate_x and location.coordinate_x < 0,
                location.coordinate_y and location.coordinate_y < 0,
                location.coordinate_z and location.coordinate_z < 0,
            ]):
                raise ValidationError(_('Coordinates must be positive values.'))

    @api.constrains('accessibility_score')
    def _check_accessibility_score(self):
        for location in self:
            if location.accessibility_score and not (1 <= location.accessibility_score <= 100):
                raise ValidationError(_('Accessibility score must be between 1 and 100.'))

    def calculate_distance(self, other_location):
        """Calculate 3D distance between two locations"""
        self.ensure_one()
        if not all([
            self.coordinate_x, self.coordinate_y, self.coordinate_z,
            other_location.coordinate_x, other_location.coordinate_y, other_location.coordinate_z
        ]):
            return 0.0
        
        dx = self.coordinate_x - other_location.coordinate_x
        dy = self.coordinate_y - other_location.coordinate_y
        dz = self.coordinate_z - other_location.coordinate_z
        
        return (dx**2 + dy**2 + dz**2) ** 0.5

    def get_available_capacity(self):
        """Get available capacity in this location"""
        self.ensure_one()
        if not self.location_capacity:
            return 0.0
        
        # Calculate used capacity from quants
        used_volume = 0.0
        quants = self.env['stock.quant'].search([
            ('location_id', '=', self.id),
            ('quantity', '>', 0)
        ])
        
        for quant in quants:
            product_volume = quant.product_id.volume or 0.0
            used_volume += product_volume * quant.quantity
        
        return self.location_capacity - used_volume
