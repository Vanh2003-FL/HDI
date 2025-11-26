# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import math


class WmsLocation(models.Model):
    _inherit = 'wms.location'

    # 3D Coordinates (Floor-Aisle-Rack-Bin addressing)
    floor_level = fields.Integer(string='Floor', default=1, help='Floor level (1-based)')
    aisle = fields.Char(string='Aisle', size=10, help='Aisle identifier (e.g., A01, A02)')
    rack = fields.Char(string='Rack', size=10, help='Rack identifier (e.g., R01, R02)')
    bin_position = fields.Char(string='Bin', size=10, help='Bin position (e.g., B01, B02)')
    
    # Cartesian coordinates for map rendering
    x_coordinate = fields.Float(string='X Coordinate', digits=(10, 2),
                                help='X position in warehouse layout (meters)')
    y_coordinate = fields.Float(string='Y Coordinate', digits=(10, 2),
                                help='Y position in warehouse layout (meters)')
    z_coordinate = fields.Float(string='Z Coordinate', digits=(10, 2),
                                help='Z position (height in meters)')
    
    # Display name with 3D address
    location_address = fields.Char(string='3D Address', compute='_compute_location_address',
                                   store=True, index=True,
                                   help='Formatted as F{floor}-{aisle}-{rack}-{bin}')
    
    # Putaway preferences
    abc_zone = fields.Selection([
        ('a', 'Zone A - High Value/Fast Moving'),
        ('b', 'Zone B - Medium Value/Medium Moving'),
        ('c', 'Zone C - Low Value/Slow Moving'),
    ], string='ABC Zone', help='ABC classification zone for putaway optimization')
    
    distance_from_receiving = fields.Float(string='Distance from Receiving (m)',
                                          compute='_compute_distances', store=True,
                                          help='Calculated distance from receiving zone')
    distance_from_picking = fields.Float(string='Distance from Picking (m)',
                                        compute='_compute_distances', store=True,
                                        help='Calculated distance from picking zone')
    
    # Putaway priority
    putaway_priority = fields.Integer(string='Putaway Priority', default=50,
                                     help='1-100, higher = preferred for putaway')
    putaway_sequence = fields.Integer(string='Putaway Sequence', default=100,
                                     help='Sequence for putaway suggestions')
    
    # Visualization
    color_code = fields.Char(string='Color Code', default='#3498db',
                            help='Hex color for map visualization')
    
    @api.depends('floor_level', 'aisle', 'rack', 'bin_position')
    def _compute_location_address(self):
        for location in self:
            parts = []
            if location.floor_level:
                parts.append(f'F{location.floor_level}')
            if location.aisle:
                parts.append(location.aisle)
            if location.rack:
                parts.append(location.rack)
            if location.bin_position:
                parts.append(location.bin_position)
            
            location.location_address = '-'.join(parts) if parts else location.name

    @api.depends('x_coordinate', 'y_coordinate', 'warehouse_id')
    def _compute_distances(self):
        for location in self:
            if not location.x_coordinate or not location.y_coordinate:
                location.distance_from_receiving = 0.0
                location.distance_from_picking = 0.0
                continue
            
            # Find receiving zone location
            receiving_zone = self.env['wms.zone'].search([
                ('warehouse_id', '=', location.warehouse_id.id),
                ('zone_type', '=', 'receiving')
            ], limit=1)
            
            if receiving_zone:
                # Get representative location in receiving zone (use first location)
                recv_loc = self.search([
                    ('zone_id', '=', receiving_zone.id),
                    ('x_coordinate', '!=', 0),
                    ('y_coordinate', '!=', 0)
                ], limit=1)
                
                if recv_loc:
                    location.distance_from_receiving = self._calculate_distance(
                        location.x_coordinate, location.y_coordinate,
                        recv_loc.x_coordinate, recv_loc.y_coordinate
                    )
            
            # Find picking zone location
            picking_zone = self.env['wms.zone'].search([
                ('warehouse_id', '=', location.warehouse_id.id),
                ('zone_type', '=', 'picking')
            ], limit=1)
            
            if picking_zone:
                pick_loc = self.search([
                    ('zone_id', '=', picking_zone.id),
                    ('x_coordinate', '!=', 0),
                    ('y_coordinate', '!=', 0)
                ], limit=1)
                
                if pick_loc:
                    location.distance_from_picking = self._calculate_distance(
                        location.x_coordinate, location.y_coordinate,
                        pick_loc.x_coordinate, pick_loc.y_coordinate
                    )

    def _calculate_distance(self, x1, y1, x2, y2):
        """Calculate Euclidean distance between two points"""
        return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

    def get_putaway_score(self, product_id, quantity):
        """Calculate putaway suitability score for this location"""
        self.ensure_one()
        score = 0
        
        # Base: Available capacity (0-40 points)
        if self.capacity > 0:
            capacity_ratio = self.available_capacity / self.capacity
            score += capacity_ratio * 40
        
        # ABC matching (0-30 points)
        if product_id.abc_classification and self.abc_zone:
            if product_id.abc_classification == self.abc_zone:
                score += 30
            elif abs(ord(product_id.abc_classification) - ord(self.abc_zone)) == 1:
                score += 15  # Adjacent zones get partial points
        
        # Distance from picking (0-20 points, closer = better for A items)
        if self.distance_from_picking > 0:
            if product_id.abc_classification == 'a':
                score += max(0, 20 - self.distance_from_picking)
            elif product_id.abc_classification == 'b':
                score += 10
        
        # Putaway priority (0-10 points)
        score += (self.putaway_priority / 100) * 10
        
        return score

    def action_view_on_map(self):
        """View location on warehouse map"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Warehouse Map'),
            'res_model': 'warehouse.map.config',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_highlight_location_id': self.id,
                'default_warehouse_id': self.warehouse_id.id,
            }
        }
