# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime, timedelta


class LogisticsTracking(models.Model):
    _name = 'logistics.tracking'
    _description = 'Shipment Tracking Information'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Tracking Number', required=True, copy=False, index=True,
                      default=lambda self: _('New'))
    
    # Related delivery
    delivery_id = fields.Many2one('wms.delivery', string='Delivery Order',
                                  ondelete='cascade', tracking=True)
    sale_order_id = fields.Many2one(related='delivery_id.sale_id', string='Sale Order', store=True)
    
    # Carrier info
    partner_id = fields.Many2one('logistics.partner', string='Carrier', required=True,
                                 tracking=True)
    service_type = fields.Selection([
        ('standard', 'Standard'),
        ('express', 'Express'),
        ('same_day', 'Same Day'),
        ('next_day', 'Next Day'),
        ('economy', 'Economy'),
    ], string='Service Type', default='standard', required=True)
    
    # Shipment details
    carrier_tracking_ref = fields.Char(string='Carrier Tracking Ref', tracking=True,
                                      help='Tracking number from carrier system')
    carrier_shipment_id = fields.Char(string='Carrier Shipment ID',
                                     help='Internal shipment ID from carrier')
    
    # Dates
    created_date = fields.Datetime(string='Created Date', default=fields.Datetime.now,
                                   tracking=True)
    shipped_date = fields.Datetime(string='Shipped Date', tracking=True)
    estimated_delivery_date = fields.Date(string='Estimated Delivery', tracking=True)
    delivered_date = fields.Datetime(string='Delivered Date', tracking=True)
    
    # Weight & dimensions
    weight = fields.Float(string='Weight (kg)', digits=(10, 2), tracking=True)
    length = fields.Float(string='Length (cm)', digits=(10, 2))
    width = fields.Float(string='Width (cm)', digits=(10, 2))
    height = fields.Float(string='Height (cm)', digits=(10, 2))
    volumetric_weight = fields.Float(string='Volumetric Weight (kg)',
                                     compute='_compute_volumetric_weight', store=True)
    chargeable_weight = fields.Float(string='Chargeable Weight (kg)',
                                    compute='_compute_chargeable_weight', store=True)
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('ready', 'Ready to Ship'),
        ('picked_up', 'Picked Up'),
        ('in_transit', 'In Transit'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('returned', 'Returned'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, required=True)
    
    # COD
    is_cod = fields.Boolean(string='COD Shipment', default=False)
    cod_amount = fields.Monetary(string='COD Amount', currency_field='currency_id')
    cod_collected = fields.Boolean(string='COD Collected', default=False)
    cod_remitted = fields.Boolean(string='COD Remitted', default=False)
    
    # Costs
    shipping_cost = fields.Monetary(string='Shipping Cost', currency_field='currency_id',
                                   tracking=True)
    cod_fee = fields.Monetary(string='COD Fee', currency_field='currency_id')
    fuel_surcharge = fields.Monetary(string='Fuel Surcharge', currency_field='currency_id')
    total_cost = fields.Monetary(string='Total Cost', compute='_compute_total_cost',
                                store=True, currency_field='currency_id')
    
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)
    
    # POD (Proof of Delivery)
    pod_signature = fields.Binary(string='POD Signature', attachment=True)
    pod_photo = fields.Binary(string='POD Photo', attachment=True)
    pod_receiver_name = fields.Char(string='Receiver Name')
    pod_notes = fields.Text(string='POD Notes')
    
    # Tracking events
    event_ids = fields.One2many('logistics.tracking.event', 'tracking_id',
                               string='Tracking Events')
    last_event = fields.Char(string='Last Event', compute='_compute_last_event')
    last_update = fields.Datetime(string='Last Update', compute='_compute_last_event')
    
    # SLA
    sla_days = fields.Integer(string='SLA Days', default=3,
                             help='Service level agreement in days')
    is_on_time = fields.Boolean(string='On Time', compute='_compute_sla_status', store=True)
    is_late = fields.Boolean(string='Late', compute='_compute_sla_status', store=True)
    delay_days = fields.Integer(string='Delay Days', compute='_compute_sla_status', store=True)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('logistics.tracking') or _('New')
        return super().create(vals)

    @api.depends('length', 'width', 'height')
    def _compute_volumetric_weight(self):
        """Calculate volumetric weight (L x W x H / 5000)"""
        for tracking in self:
            if tracking.length and tracking.width and tracking.height:
                tracking.volumetric_weight = (tracking.length * tracking.width * tracking.height) / 5000
            else:
                tracking.volumetric_weight = 0.0

    @api.depends('weight', 'volumetric_weight')
    def _compute_chargeable_weight(self):
        """Chargeable weight = max(actual weight, volumetric weight)"""
        for tracking in self:
            tracking.chargeable_weight = max(tracking.weight or 0, tracking.volumetric_weight or 0)

    @api.depends('shipping_cost', 'cod_fee', 'fuel_surcharge')
    def _compute_total_cost(self):
        for tracking in self:
            tracking.total_cost = (tracking.shipping_cost or 0) + \
                                 (tracking.cod_fee or 0) + \
                                 (tracking.fuel_surcharge or 0)

    @api.depends('event_ids')
    def _compute_last_event(self):
        for tracking in self:
            last_event = tracking.event_ids.sorted('event_time', reverse=True)[:1]
            if last_event:
                tracking.last_event = last_event.event_description
                tracking.last_update = last_event.event_time
            else:
                tracking.last_event = ''
                tracking.last_update = False

    @api.depends('shipped_date', 'delivered_date', 'estimated_delivery_date', 'sla_days')
    def _compute_sla_status(self):
        for tracking in self:
            if not tracking.shipped_date:
                tracking.is_on_time = False
                tracking.is_late = False
                tracking.delay_days = 0
                continue
            
            # Calculate expected delivery date
            expected_delivery = tracking.shipped_date + timedelta(days=tracking.sla_days)
            
            if tracking.delivered_date:
                # Already delivered - check if on time
                tracking.is_on_time = tracking.delivered_date <= expected_delivery
                tracking.is_late = tracking.delivered_date > expected_delivery
                
                if tracking.is_late:
                    tracking.delay_days = (tracking.delivered_date.date() - expected_delivery.date()).days
                else:
                    tracking.delay_days = 0
            else:
                # Not yet delivered - check if overdue
                now = datetime.now()
                tracking.is_late = now > expected_delivery
                tracking.is_on_time = False
                
                if tracking.is_late:
                    tracking.delay_days = (now.date() - expected_delivery.date()).days
                else:
                    tracking.delay_days = 0

    def action_create_shipment(self):
        """Create shipment with carrier API"""
        self.ensure_one()
        
        if not self.partner_id:
            raise UserError(_('Please select a carrier first!'))
        
        # Call carrier-specific API
        if self.partner_id.partner_type == 'viettel_post':
            result = self._create_viettel_post_shipment()
        elif self.partner_id.partner_type == 'ghn':
            result = self._create_ghn_shipment()
        elif self.partner_id.partner_type == 'jnt':
            result = self._create_jnt_shipment()
        elif self.partner_id.partner_type == 'ninja_van':
            result = self._create_ninja_van_shipment()
        else:
            raise UserError(_('Shipment creation not implemented for this carrier!'))
        
        if result:
            self.write({
                'state': 'ready',
                'carrier_tracking_ref': result.get('tracking_ref'),
                'carrier_shipment_id': result.get('shipment_id'),
            })
            
            # Log event
            self.env['logistics.tracking.event'].create({
                'tracking_id': self.id,
                'event_type': 'created',
                'event_description': 'Shipment created with carrier',
                'event_time': fields.Datetime.now(),
            })

    def _create_viettel_post_shipment(self):
        """Create shipment with Viettel Post API"""
        # Implement Viettel Post API call
        return {'tracking_ref': 'VTP123456', 'shipment_id': 'SHIP001'}

    def _create_ghn_shipment(self):
        """Create shipment with GHN API"""
        # Implement GHN API call
        return {'tracking_ref': 'GHN123456', 'shipment_id': 'SHIP002'}

    def _create_jnt_shipment(self):
        """Create shipment with J&T API"""
        return {'tracking_ref': 'JNT123456', 'shipment_id': 'SHIP003'}

    def _create_ninja_van_shipment(self):
        """Create shipment with Ninja Van API"""
        return {'tracking_ref': 'NV123456', 'shipment_id': 'SHIP004'}

    def action_update_tracking(self):
        """Update tracking status from carrier API"""
        self.ensure_one()
        # Implement carrier API polling
        pass

    def action_print_label(self):
        """Print shipping label"""
        self.ensure_one()
        return self.env.ref('hdi_logistics_partner.report_shipping_label').report_action(self)


class LogisticsTrackingEvent(models.Model):
    _name = 'logistics.tracking.event'
    _description = 'Tracking Event'
    _order = 'event_time desc'

    tracking_id = fields.Many2one('logistics.tracking', string='Tracking', required=True,
                                  ondelete='cascade')
    
    event_type = fields.Selection([
        ('created', 'Created'),
        ('picked_up', 'Picked Up'),
        ('arrived_hub', 'Arrived at Hub'),
        ('departed_hub', 'Departed Hub'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('delivery_failed', 'Delivery Failed'),
        ('returned', 'Returned'),
        ('exception', 'Exception'),
    ], string='Event Type', required=True)
    
    event_time = fields.Datetime(string='Event Time', required=True, default=fields.Datetime.now)
    event_description = fields.Char(string='Description', required=True)
    location = fields.Char(string='Location')
    notes = fields.Text(string='Notes')
