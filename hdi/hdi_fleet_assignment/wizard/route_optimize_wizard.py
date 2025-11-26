# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class RouteOptimizeWizard(models.TransientModel):
    _name = 'route.optimize.wizard'
    _description = 'Route Optimization Wizard'

    delivery_date = fields.Date(string='Delivery Date', required=True,
                                default=fields.Date.today)
    warehouse_id = fields.Many2one('wms.warehouse', string='Warehouse', required=True)
    
    # Delivery selection
    delivery_ids = fields.Many2many('wms.delivery', string='Deliveries to Assign',
                                   domain=[('state', '=', 'ready')])
    delivery_count = fields.Integer(string='Selected Deliveries',
                                   compute='_compute_delivery_count')
    
    # Vehicle selection
    vehicle_ids = fields.Many2many('fleet.vehicle', string='Available Vehicles',
                                  domain=[('availability_status', '=', 'available')])
    vehicle_count = fields.Integer(string='Available Vehicles',
                                  compute='_compute_vehicle_count')
    
    # Optimization settings
    optimization_method = fields.Selection([
        ('nearest_neighbor', 'Nearest Neighbor (Fast)'),
        ('genetic_algorithm', 'Genetic Algorithm (Better)'),
        ('manual', 'Manual Assignment'),
    ], string='Optimization Method', default='nearest_neighbor', required=True)
    
    max_stops_per_vehicle = fields.Integer(string='Max Stops per Vehicle', default=10)
    max_weight_utilization = fields.Float(string='Max Weight Utilization (%)', default=90)
    max_volume_utilization = fields.Float(string='Max Volume Utilization (%)', default=80)
    
    # Results
    route_plan_ids = fields.Many2many('vehicle.route.plan', string='Generated Routes',
                                     readonly=True)
    total_routes = fields.Integer(string='Total Routes', compute='_compute_results')
    total_distance = fields.Float(string='Total Distance (km)', compute='_compute_results')

    @api.depends('delivery_ids')
    def _compute_delivery_count(self):
        for wizard in self:
            wizard.delivery_count = len(wizard.delivery_ids)

    @api.depends('vehicle_ids')
    def _compute_vehicle_count(self):
        for wizard in self:
            wizard.vehicle_count = len(wizard.vehicle_ids)

    @api.depends('route_plan_ids')
    def _compute_results(self):
        for wizard in self:
            wizard.total_routes = len(wizard.route_plan_ids)
            wizard.total_distance = sum(wizard.route_plan_ids.mapped('total_distance_km'))

    @api.onchange('warehouse_id', 'delivery_date')
    def _onchange_warehouse_date(self):
        """Auto-load pending deliveries"""
        if self.warehouse_id and self.delivery_date:
            deliveries = self.env['wms.delivery'].search([
                ('warehouse_id', '=', self.warehouse_id.id),
                ('scheduled_date', '=', self.delivery_date),
                ('state', '=', 'ready'),
                ('vehicle_id', '=', False),  # Not yet assigned
            ])
            
            self.delivery_ids = deliveries

    @api.onchange('warehouse_id')
    def _onchange_warehouse_vehicles(self):
        """Auto-load available vehicles"""
        if self.warehouse_id:
            vehicles = self.env['fleet.vehicle'].search([
                ('warehouse_id', '=', self.warehouse_id.id),
                ('availability_status', '=', 'available'),
            ])
            
            self.vehicle_ids = vehicles

    def action_optimize(self):
        """Run route optimization"""
        self.ensure_one()
        
        if not self.delivery_ids:
            raise UserError(_('Please select deliveries to optimize!'))
        
        if not self.vehicle_ids:
            raise UserError(_('No vehicles available!'))
        
        # Run optimization algorithm
        if self.optimization_method == 'nearest_neighbor':
            route_plans = self._optimize_nearest_neighbor()
        elif self.optimization_method == 'genetic_algorithm':
            route_plans = self._optimize_genetic_algorithm()
        else:
            route_plans = self._manual_assignment()
        
        self.route_plan_ids = route_plans
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'route.optimize.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def _optimize_nearest_neighbor(self):
        """Greedy nearest neighbor algorithm"""
        
        route_plans = self.env['vehicle.route.plan']
        deliveries = self.delivery_ids
        vehicles = self.vehicle_ids
        
        vehicle_idx = 0
        
        while deliveries and vehicle_idx < len(vehicles):
            vehicle = vehicles[vehicle_idx]
            
            # Create route plan for this vehicle
            route_plan = self.env['vehicle.route.plan'].create({
                'name': f'Route {self.delivery_date} - {vehicle.name}',
                'delivery_date': self.delivery_date,
                'optimization_method': 'nearest_neighbor',
                'start_location_id': self.warehouse_id.location_id.id,
                'start_latitude': self.warehouse_id.partner_id.partner_latitude or 0,
                'start_longitude': self.warehouse_id.partner_id.partner_longitude or 0,
            })
            
            # Assign deliveries to this vehicle
            vehicle_load_weight = 0
            vehicle_load_volume = 0
            stops = 0
            
            remaining_deliveries = deliveries
            
            for delivery in remaining_deliveries:
                # Calculate delivery load
                delivery_weight = sum(delivery.line_ids.mapped(
                    lambda l: l.product_id.weight * l.quantity_done
                ))
                delivery_volume = sum(delivery.line_ids.mapped(
                    lambda l: l.product_id.volume * l.quantity_done
                ))
                
                # Check if vehicle can accommodate
                weight_util = ((vehicle_load_weight + delivery_weight) / vehicle.max_weight_kg * 100) \
                              if vehicle.max_weight_kg > 0 else 0
                volume_util = ((vehicle_load_volume + delivery_volume) / vehicle.max_volume_m3 * 100) \
                              if vehicle.max_volume_m3 > 0 else 0
                
                if (weight_util <= self.max_weight_utilization and 
                    volume_util <= self.max_volume_utilization and
                    stops < self.max_stops_per_vehicle):
                    
                    # Create assignment
                    assignment = self.env['picking.vehicle.assign'].create({
                        'vehicle_id': vehicle.id,
                        'delivery_ids': [(6, 0, [delivery.id])],
                        'delivery_date': self.delivery_date,
                        'route_plan_id': route_plan.id,
                        'sequence': stops + 1,
                    })
                    
                    vehicle_load_weight += delivery_weight
                    vehicle_load_volume += delivery_volume
                    stops += 1
                    
                    deliveries -= delivery
            
            # Optimize this route
            route_plan.action_optimize_route()
            route_plans |= route_plan
            
            vehicle_idx += 1
        
        return route_plans

    def _optimize_genetic_algorithm(self):
        """Genetic algorithm optimization (simplified)"""
        # For now, use nearest neighbor
        return self._optimize_nearest_neighbor()

    def _manual_assignment(self):
        """Manual assignment - no optimization"""
        # Create single route plan with all deliveries
        route_plan = self.env['vehicle.route.plan'].create({
            'name': f'Manual Route {self.delivery_date}',
            'delivery_date': self.delivery_date,
            'optimization_method': 'manual',
        })
        
        return route_plan

    def action_confirm_routes(self):
        """Confirm and assign routes"""
        self.ensure_one()
        
        if not self.route_plan_ids:
            raise UserError(_('No routes generated yet! Please run optimization first.'))
        
        # Assign all routes
        for route_plan in self.route_plan_ids:
            for assignment in route_plan.assignment_ids:
                assignment.action_assign()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('%d routes confirmed and assigned!') % len(self.route_plan_ids),
                'type': 'success',
                'next': {
                    'type': 'ir.actions.act_window',
                    'res_model': 'vehicle.route.plan',
                    'view_mode': 'tree,form',
                    'domain': [('id', 'in', self.route_plan_ids.ids)],
                },
            }
        }
