# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta


class PickingVehicleAssign(models.Model):
    _name = 'picking.vehicle.assign'
    _description = 'Vehicle Assignment for Deliveries'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'delivery_date desc, sequence'

    name = fields.Char(string='Assignment Reference', required=True, copy=False,
                      default=lambda self: _('New'))
    sequence = fields.Integer(string='Stop Sequence', default=1,
                             help='Order of delivery stops in the route')
    
    # Vehicle & Driver
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', required=True,
                                tracking=True)
    driver_id = fields.Many2one('res.partner', string='Driver', tracking=True,
                               domain=[('is_driver', '=', True)])
    
    # Deliveries
    delivery_ids = fields.Many2many('wms.delivery', string='Deliveries',
                                   help='Multiple deliveries in one route')
    delivery_count = fields.Integer(string='Delivery Count',
                                   compute='_compute_delivery_count')
    
    # Route planning
    route_plan_id = fields.Many2one('vehicle.route.plan', string='Route Plan',
                                   ondelete='cascade')
    planned_distance_km = fields.Float(string='Planned Distance (km)', digits=(10, 2))
    actual_distance_km = fields.Float(string='Actual Distance (km)', digits=(10, 2),
                                     tracking=True)
    
    # Dates
    delivery_date = fields.Date(string='Delivery Date', required=True,
                               default=fields.Date.today, tracking=True)
    planned_start_time = fields.Datetime(string='Planned Start', tracking=True)
    planned_end_time = fields.Datetime(string='Planned End')
    actual_start_time = fields.Datetime(string='Actual Start', tracking=True)
    actual_end_time = fields.Datetime(string='Actual End', tracking=True)
    
    # Load details
    total_weight_kg = fields.Float(string='Total Weight (kg)', compute='_compute_load',
                                  store=True)
    total_volume_m3 = fields.Float(string='Total Volume (m³)', compute='_compute_load',
                                  store=True)
    total_pallets = fields.Integer(string='Total Pallets', compute='_compute_load',
                                  store=True)
    
    # Capacity utilization
    weight_utilization = fields.Float(string='Weight Utilization (%)',
                                     compute='_compute_utilization')
    volume_utilization = fields.Float(string='Volume Utilization (%)',
                                     compute='_compute_utilization')
    
    # Fuel tracking
    fuel_consumed = fields.Float(string='Fuel Consumed (L)', digits=(10, 2))
    fuel_cost = fields.Monetary(string='Fuel Cost', currency_field='currency_id')
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('assigned', 'Assigned'),
        ('in_transit', 'In Transit'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, required=True)
    
    # SLA
    is_on_time = fields.Boolean(string='On Time', compute='_compute_sla')
    delay_minutes = fields.Integer(string='Delay (minutes)', compute='_compute_sla')
    
    # Notes
    notes = fields.Text(string='Assignment Notes')
    
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('picking.vehicle.assign') or _('New')
        return super().create(vals)

    @api.depends('delivery_ids')
    def _compute_delivery_count(self):
        for assignment in self:
            assignment.delivery_count = len(assignment.delivery_ids)

    @api.depends('delivery_ids')
    def _compute_load(self):
        for assignment in self:
            total_weight = 0
            total_volume = 0
            total_pallets = 0
            
            for delivery in assignment.delivery_ids:
                for line in delivery.line_ids:
                    product = line.product_id
                    qty = line.quantity_done or line.quantity
                    
                    total_weight += product.weight * qty
                    total_volume += product.volume * qty
                    
                    # Estimate pallets (assuming standard pallet = 1m³)
                    if product.volume > 0:
                        total_pallets += int((product.volume * qty) / 1.0)
            
            assignment.total_weight_kg = total_weight
            assignment.total_volume_m3 = total_volume
            assignment.total_pallets = max(1, total_pallets)  # At least 1 pallet

    @api.depends('total_weight_kg', 'total_volume_m3', 'vehicle_id')
    def _compute_utilization(self):
        for assignment in self:
            if assignment.vehicle_id:
                if assignment.vehicle_id.max_weight_kg > 0:
                    assignment.weight_utilization = (assignment.total_weight_kg / 
                                                    assignment.vehicle_id.max_weight_kg) * 100
                else:
                    assignment.weight_utilization = 0
                
                if assignment.vehicle_id.max_volume_m3 > 0:
                    assignment.volume_utilization = (assignment.total_volume_m3 / 
                                                    assignment.vehicle_id.max_volume_m3) * 100
                else:
                    assignment.volume_utilization = 0
            else:
                assignment.weight_utilization = 0
                assignment.volume_utilization = 0

    @api.depends('planned_end_time', 'actual_end_time', 'state')
    def _compute_sla(self):
        for assignment in self:
            if assignment.state == 'completed' and assignment.planned_end_time and assignment.actual_end_time:
                assignment.is_on_time = assignment.actual_end_time <= assignment.planned_end_time
                
                if not assignment.is_on_time:
                    delta = assignment.actual_end_time - assignment.planned_end_time
                    assignment.delay_minutes = int(delta.total_seconds() / 60)
                else:
                    assignment.delay_minutes = 0
            else:
                assignment.is_on_time = False
                assignment.delay_minutes = 0

    def action_assign(self):
        """Assign vehicle to deliveries"""
        self.ensure_one()
        
        # Validate vehicle availability
        if self.vehicle_id.availability_status not in ['available']:
            raise UserError(_('Vehicle %s is not available!') % self.vehicle_id.name)
        
        # Check capacity
        if self.weight_utilization > 100:
            raise UserError(_('Total weight exceeds vehicle capacity!'))
        
        if self.volume_utilization > 100:
            raise UserError(_('Total volume exceeds vehicle capacity!'))
        
        # Update vehicle status
        self.vehicle_id.write({'availability_status': 'assigned'})
        
        # Update delivery orders
        self.delivery_ids.write({
            'vehicle_id': self.vehicle_id.id,
            'driver_id': self.driver_id.id,
        })
        
        self.write({'state': 'assigned'})
        
        # Log activity
        self.message_post(body=_('Vehicle %s assigned to %d deliveries') % 
                         (self.vehicle_id.name, len(self.delivery_ids)))

    def action_start_transit(self):
        """Start delivery transit"""
        self.ensure_one()
        
        self.write({
            'state': 'in_transit',
            'actual_start_time': fields.Datetime.now(),
        })
        
        # Update vehicle status
        self.vehicle_id.write({'availability_status': 'in_transit'})
        
        # Notify driver (placeholder for mobile app notification)
        self.message_post(body=_('Delivery route started'))

    def action_complete(self):
        """Complete delivery assignment"""
        self.ensure_one()
        
        self.write({
            'state': 'completed',
            'actual_end_time': fields.Datetime.now(),
        })
        
        # Update vehicle status back to available
        self.vehicle_id.write({'availability_status': 'available'})
        
        self.message_post(body=_('Delivery assignment completed'))

    def action_cancel(self):
        """Cancel assignment"""
        self.ensure_one()
        
        self.write({'state': 'cancelled'})
        
        # Free up vehicle
        self.vehicle_id.write({'availability_status': 'available'})

    def action_view_deliveries(self):
        """View assigned deliveries"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Assigned Deliveries'),
            'res_model': 'wms.delivery',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.delivery_ids.ids)],
        }

    def action_view_route_map(self):
        """View route on map"""
        self.ensure_one()
        
        # Return map view (implement with Google Maps API or similar)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Route Map'),
            'res_model': 'vehicle.route.plan',
            'res_id': self.route_plan_id.id if self.route_plan_id else False,
            'view_mode': 'form',
            'target': 'new',
        }
