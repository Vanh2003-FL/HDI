# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class VehicleGpsTracking(models.Model):
    _name = 'vehicle.gps.tracking'
    _description = 'Vehicle GPS Tracking History'
    _order = 'timestamp desc'
    _rec_name = 'vehicle_id'

    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', required=True,
                                 ondelete='cascade', index=True)
    assignment_id = fields.Many2one('picking.vehicle.assign', string='Assignment',
                                   ondelete='set null')
    
    # GPS coordinates
    latitude = fields.Float(string='Latitude', required=True, digits=(10, 6))
    longitude = fields.Float(string='Longitude', required=True, digits=(10, 6))
    altitude = fields.Float(string='Altitude (m)', digits=(10, 2))
    accuracy = fields.Float(string='Accuracy (m)', digits=(10, 2),
                           help='GPS accuracy radius in meters')
    
    # Motion data
    speed = fields.Float(string='Speed (km/h)', digits=(10, 2))
    heading = fields.Float(string='Heading (degrees)', digits=(10, 2),
                          help='Direction: 0=North, 90=East, 180=South, 270=West')
    
    # Timestamp
    timestamp = fields.Datetime(string='Timestamp', required=True,
                               default=fields.Datetime.now, index=True)
    
    # Status
    is_moving = fields.Boolean(string='Is Moving', compute='_compute_is_moving')
    is_idle = fields.Boolean(string='Is Idle', compute='_compute_is_moving')
    
    # Battery (for tracking device)
    battery_level = fields.Integer(string='Battery Level (%)')
    
    # Address (reverse geocoding)
    address = fields.Char(string='Address', help='Reverse geocoded address')

    @api.depends('speed')
    def _compute_is_moving(self):
        for tracking in self:
            tracking.is_moving = tracking.speed > 5  # Moving if speed > 5 km/h
            tracking.is_idle = not tracking.is_moving

    def action_view_on_map(self):
        """View this location on map"""
        self.ensure_one()
        
        # Open map view centered on this location
        return {
            'type': 'ir.actions.act_url',
            'url': f'https://www.google.com/maps?q={self.latitude},{self.longitude}',
            'target': 'new',
        }

    @api.model
    def create_tracking_from_device(self, device_id, data):
        """Create tracking record from GPS device data (API endpoint)"""
        
        # Find vehicle by GPS device ID
        vehicle = self.env['fleet.vehicle'].search([
            ('gps_device_id', '=', device_id)
        ], limit=1)
        
        if not vehicle:
            return {'error': 'Vehicle not found for device ID'}
        
        # Create tracking record
        tracking = self.create({
            'vehicle_id': vehicle.id,
            'latitude': data.get('latitude'),
            'longitude': data.get('longitude'),
            'altitude': data.get('altitude', 0),
            'speed': data.get('speed', 0),
            'heading': data.get('heading', 0),
            'accuracy': data.get('accuracy', 0),
            'battery_level': data.get('battery', 100),
            'timestamp': data.get('timestamp', fields.Datetime.now()),
        })
        
        # Update vehicle current location
        vehicle.update_gps_location(
            latitude=data.get('latitude'),
            longitude=data.get('longitude'),
            speed=data.get('speed', 0)
        )
        
        return {'success': True, 'tracking_id': tracking.id}


class VehicleGeofence(models.Model):
    _name = 'vehicle.geofence'
    _description = 'Vehicle Geofencing Area'

    name = fields.Char(string='Geofence Name', required=True)
    
    # Center point
    center_latitude = fields.Float(string='Center Latitude', required=True, digits=(10, 6))
    center_longitude = fields.Float(string='Center Longitude', required=True, digits=(10, 6))
    radius_meters = fields.Float(string='Radius (meters)', required=True, default=100)
    
    # Type
    fence_type = fields.Selection([
        ('warehouse', 'Warehouse'),
        ('customer', 'Customer Location'),
        ('restricted', 'Restricted Area'),
        ('service', 'Service Area'),
    ], string='Type', default='warehouse')
    
    # Actions
    action_on_entry = fields.Selection([
        ('none', 'None'),
        ('notify', 'Send Notification'),
        ('log', 'Log Entry'),
    ], string='Action on Entry', default='log')
    
    action_on_exit = fields.Selection([
        ('none', 'None'),
        ('notify', 'Send Notification'),
        ('log', 'Log Exit'),
    ], string='Action on Exit', default='log')
    
    active = fields.Boolean(string='Active', default=True)

    def is_point_inside(self, latitude, longitude):
        """Check if point is inside geofence"""
        self.ensure_one()
        
        # Calculate distance from center
        R = 6371000  # Earth radius in meters
        
        import math
        
        dlat = math.radians(latitude - self.center_latitude)
        dlon = math.radians(longitude - self.center_longitude)
        
        a = (math.sin(dlat / 2) ** 2 + 
             math.cos(math.radians(self.center_latitude)) * 
             math.cos(math.radians(latitude)) * 
             math.sin(dlon / 2) ** 2)
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance = R * c
        
        return distance <= self.radius_meters
