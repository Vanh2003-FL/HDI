# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    # WMS Integration
    warehouse_id = fields.Many2one('wms.warehouse', string='Home Warehouse',
                                   help='Default warehouse for this vehicle')
    
    # Vehicle capacity
    max_weight_kg = fields.Float(string='Max Weight (kg)', digits=(10, 2),
                                 help='Maximum weight capacity')
    max_volume_m3 = fields.Float(string='Max Volume (m³)', digits=(10, 3),
                                 help='Maximum volume capacity')
    max_pallets = fields.Integer(string='Max Pallets',
                                 help='Maximum number of pallets')
    
    # Vehicle type for delivery
    vehicle_category = fields.Selection([
        ('motorcycle', 'Motorcycle'),
        ('van', 'Van'),
        ('truck_small', 'Small Truck (1-3 ton)'),
        ('truck_medium', 'Medium Truck (3-7 ton)'),
        ('truck_large', 'Large Truck (7-15 ton)'),
        ('trailer', 'Trailer (15+ ton)'),
    ], string='Vehicle Category', default='van')
    
    # GPS tracking
    gps_device_id = fields.Char(string='GPS Device ID')
    has_gps = fields.Boolean(string='GPS Enabled', default=False)
    last_gps_update = fields.Datetime(string='Last GPS Update', readonly=True)
    current_latitude = fields.Float(string='Current Latitude', digits=(10, 6), readonly=True)
    current_longitude = fields.Float(string='Current Longitude', digits=(10, 6), readonly=True)
    current_speed = fields.Float(string='Current Speed (km/h)', readonly=True)
    
    # Availability
    availability_status = fields.Selection([
        ('available', 'Available'),
        ('assigned', 'Assigned'),
        ('in_transit', 'In Transit'),
        ('maintenance', 'Maintenance'),
        ('unavailable', 'Unavailable'),
    ], string='Availability', default='available', tracking=True)
    
    # Statistics
    total_deliveries = fields.Integer(string='Total Deliveries',
                                      compute='_compute_statistics')
    total_distance_km = fields.Float(string='Total Distance (km)',
                                     compute='_compute_statistics')
    average_fuel_consumption = fields.Float(string='Avg Fuel (L/100km)',
                                           compute='_compute_statistics')
    on_time_delivery_rate = fields.Float(string='On-Time Rate (%)',
                                         compute='_compute_statistics')
    
    # Assignments
    assignment_ids = fields.One2many('picking.vehicle.assign', 'vehicle_id',
                                    string='Assignments')
    active_assignment_count = fields.Integer(string='Active Assignments',
                                            compute='_compute_active_assignments')

    @api.depends('assignment_ids')
    def _compute_statistics(self):
        for vehicle in self:
            assignments = vehicle.assignment_ids.filtered(lambda a: a.state == 'completed')
            
            vehicle.total_deliveries = len(assignments)
            vehicle.total_distance_km = sum(assignments.mapped('actual_distance_km'))
            
            # Fuel consumption (if tracked)
            if assignments and any(a.fuel_consumed for a in assignments):
                total_fuel = sum(assignments.mapped('fuel_consumed'))
                total_distance = vehicle.total_distance_km
                if total_distance > 0:
                    vehicle.average_fuel_consumption = (total_fuel / total_distance) * 100
                else:
                    vehicle.average_fuel_consumption = 0
            else:
                vehicle.average_fuel_consumption = 0
            
            # On-time rate
            if assignments:
                on_time = assignments.filtered(lambda a: a.is_on_time)
                vehicle.on_time_delivery_rate = (len(on_time) / len(assignments)) * 100
            else:
                vehicle.on_time_delivery_rate = 0

    @api.depends('assignment_ids')
    def _compute_active_assignments(self):
        for vehicle in self:
            vehicle.active_assignment_count = len(vehicle.assignment_ids.filtered(
                lambda a: a.state in ['draft', 'assigned', 'in_transit']
            ))

    def action_view_assignments(self):
        """View vehicle assignments"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Vehicle Assignments - %s') % self.name,
            'res_model': 'picking.vehicle.assign',
            'view_mode': 'tree,form',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {'default_vehicle_id': self.id},
        }

    def action_view_gps_tracking(self):
        """View GPS tracking history"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('GPS Tracking - %s') % self.name,
            'res_model': 'vehicle.gps.tracking',
            'view_mode': 'tree,map',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {'default_vehicle_id': self.id},
        }

    def update_gps_location(self, latitude, longitude, speed=0):
        """Update vehicle GPS location (called from mobile app or GPS device)"""
        self.ensure_one()
        
        self.write({
            'current_latitude': latitude,
            'current_longitude': longitude,
            'current_speed': speed,
            'last_gps_update': fields.Datetime.now(),
        })
        
        # Create GPS tracking record
        self.env['vehicle.gps.tracking'].create({
            'vehicle_id': self.id,
            'latitude': latitude,
            'longitude': longitude,
            'speed': speed,
            'timestamp': fields.Datetime.now(),
        })
        
        # Check geofencing alerts
        self._check_geofencing()

    def _check_geofencing(self):
        """Check if vehicle entered/exited geofenced areas"""
        # Implement geofencing logic
        pass
