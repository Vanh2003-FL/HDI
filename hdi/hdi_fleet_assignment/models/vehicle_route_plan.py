# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import json
import math


class VehicleRoutePlan(models.Model):
    _name = 'vehicle.route.plan'
    _description = 'Vehicle Route Planning'
    _order = 'delivery_date desc'

    name = fields.Char(string='Route Name', required=True)
    delivery_date = fields.Date(string='Delivery Date', required=True,
                               default=fields.Date.today)
    
    # Assignments (stops)
    assignment_ids = fields.One2many('picking.vehicle.assign', 'route_plan_id',
                                    string='Route Stops')
    stop_count = fields.Integer(string='Number of Stops',
                               compute='_compute_stop_count')
    
    # Route optimization
    optimization_method = fields.Selection([
        ('manual', 'Manual Sequence'),
        ('nearest_neighbor', 'Nearest Neighbor'),
        ('genetic_algorithm', 'Genetic Algorithm'),
        ('google_maps', 'Google Maps API'),
    ], string='Optimization Method', default='nearest_neighbor')
    
    is_optimized = fields.Boolean(string='Route Optimized', default=False)
    
    # Route details
    total_distance_km = fields.Float(string='Total Distance (km)', digits=(10, 2),
                                    compute='_compute_route_details', store=True)
    estimated_duration_hours = fields.Float(string='Estimated Duration (hours)',
                                           digits=(10, 2),
                                           compute='_compute_route_details', store=True)
    
    # Starting point
    start_location_id = fields.Many2one('wms.location', string='Start Location',
                                       help='Usually warehouse location')
    start_latitude = fields.Float(string='Start Lat', digits=(10, 6))
    start_longitude = fields.Float(string='Start Lon', digits=(10, 6))
    
    # Route map data (JSON)
    route_coordinates = fields.Text(string='Route Coordinates (JSON)',
                                   help='GeoJSON format for map rendering')
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ], string='Status', default='draft')

    @api.depends('assignment_ids')
    def _compute_stop_count(self):
        for route in self:
            route.stop_count = len(route.assignment_ids)

    @api.depends('assignment_ids', 'assignment_ids.planned_distance_km')
    def _compute_route_details(self):
        for route in self:
            route.total_distance_km = sum(route.assignment_ids.mapped('planned_distance_km'))
            
            # Estimate duration: distance / avg speed (40 km/h) + stop time (15 min per stop)
            if route.total_distance_km > 0:
                travel_time = route.total_distance_km / 40  # hours
                stop_time = len(route.assignment_ids) * 0.25  # 15 min = 0.25 hour
                route.estimated_duration_hours = travel_time + stop_time
            else:
                route.estimated_duration_hours = 0

    def action_optimize_route(self):
        """Optimize route sequence"""
        self.ensure_one()
        
        if self.optimization_method == 'nearest_neighbor':
            self._optimize_nearest_neighbor()
        elif self.optimization_method == 'genetic_algorithm':
            self._optimize_genetic_algorithm()
        elif self.optimization_method == 'google_maps':
            self._optimize_google_maps()
        
        self.write({'is_optimized': True})
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Route optimized! Total distance: %.2f km') % self.total_distance_km,
                'type': 'success',
            }
        }

    def _optimize_nearest_neighbor(self):
        """Nearest neighbor algorithm for TSP"""
        assignments = self.assignment_ids
        
        if not assignments:
            return
        
        # Start from warehouse
        current_lat = self.start_latitude or 0
        current_lon = self.start_longitude or 0
        
        remaining = assignments
        sequence = 1
        
        while remaining:
            # Find nearest delivery
            nearest = None
            min_distance = float('inf')
            
            for assignment in remaining:
                # Get delivery location (use first delivery's destination)
                if assignment.delivery_ids:
                    delivery = assignment.delivery_ids[0]
                    dest_lat = delivery.partner_shipping_id.partner_latitude or 0
                    dest_lon = delivery.partner_shipping_id.partner_longitude or 0
                    
                    distance = self._calculate_distance(current_lat, current_lon,
                                                       dest_lat, dest_lon)
                    
                    if distance < min_distance:
                        min_distance = distance
                        nearest = assignment
            
            if nearest:
                nearest.write({
                    'sequence': sequence,
                    'planned_distance_km': min_distance,
                })
                
                # Update current position
                if nearest.delivery_ids:
                    delivery = nearest.delivery_ids[0]
                    current_lat = delivery.partner_shipping_id.partner_latitude or 0
                    current_lon = delivery.partner_shipping_id.partner_longitude or 0
                
                remaining -= nearest
                sequence += 1

    def _optimize_genetic_algorithm(self):
        """Genetic algorithm for route optimization (placeholder)"""
        # Implement GA optimization
        self._optimize_nearest_neighbor()  # Fallback

    def _optimize_google_maps(self):
        """Google Maps Distance Matrix API optimization"""
        # Implement Google Maps API integration
        self._optimize_nearest_neighbor()  # Fallback

    def _calculate_distance(self, lat1, lon1, lat2, lon2):
        """Calculate haversine distance between two points"""
        R = 6371  # Earth radius in km
        
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = (math.sin(dlat / 2) ** 2 + 
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
             math.sin(dlon / 2) ** 2)
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c

    def action_view_map(self):
        """View route on map"""
        self.ensure_one()
        
        # Generate GeoJSON for map rendering
        self._generate_route_geojson()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Route Map'),
            'res_model': 'vehicle.route.plan',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def _generate_route_geojson(self):
        """Generate GeoJSON for route visualization"""
        coordinates = []
        
        # Start point
        if self.start_latitude and self.start_longitude:
            coordinates.append([self.start_longitude, self.start_latitude])
        
        # Add delivery points in sequence
        for assignment in self.assignment_ids.sorted('sequence'):
            for delivery in assignment.delivery_ids:
                lat = delivery.partner_shipping_id.partner_latitude
                lon = delivery.partner_shipping_id.partner_longitude
                
                if lat and lon:
                    coordinates.append([lon, lat])
        
        # Create GeoJSON
        geojson = {
            'type': 'LineString',
            'coordinates': coordinates,
        }
        
        self.route_coordinates = json.dumps(geojson)
