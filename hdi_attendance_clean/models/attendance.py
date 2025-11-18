# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    # Add HDI specific fields
    work_location_id = fields.Many2one('hdi.work.location', string='Work Location', tracking=True)
    
    # GPS coordinates for check-in
    checkin_latitude = fields.Float(string='Check-in Latitude', digits=(10, 7))
    checkin_longitude = fields.Float(string='Check-in Longitude', digits=(10, 7))
    
    # GPS coordinates for check-out
    checkout_latitude = fields.Float(string='Check-out Latitude', digits=(10, 7))
    checkout_longitude = fields.Float(string='Check-out Longitude', digits=(10, 7))
    
    # Color for calendar view
    color = fields.Integer(string="Color", compute='_compute_color', store=False)
    warning_message = fields.Text(string='Warning Message', compute='_compute_color')
    
    @api.depends('check_out', 'worked_hours')
    def _compute_color(self):
        for rec in self:
            warning_message = []
            color = 10  # Green by default
            
            if not rec.check_out:
                warning_message.append('Chưa check-out')
                color = 1  # Red
            elif rec.worked_hours < 7.5:
                warning_message.append('Không đủ giờ công')
                color = 1  # Red
            
            rec.color = color
            rec.warning_message = '\n'.join(warning_message) if warning_message else False

    @api.model
    def create(self, vals):
        # Get GPS coordinates from context
        if self._context.get('latitude'):
            vals['checkin_latitude'] = self._context.get('latitude')
            vals['checkin_longitude'] = self._context.get('longitude')
        
        # Get work location from context
        if self._context.get('hdi_location_id'):
            vals['work_location_id'] = self._context.get('hdi_location_id')
        
        return super(HrAttendance, self).create(vals)

    def write(self, vals):
        # Get GPS coordinates for checkout from context
        if 'check_out' in vals and self._context.get('latitude'):
            vals['checkout_latitude'] = self._context.get('latitude')
            vals['checkout_longitude'] = self._context.get('longitude')
        
        return super(HrAttendance, self).write(vals)

