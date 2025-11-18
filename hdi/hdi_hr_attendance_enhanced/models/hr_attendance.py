# -*- coding: utf-8 -*-

import logging
from datetime import datetime, timedelta
from math import radians, sin, cos, sqrt, atan2

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

try:
    from geopy.geocoders import Nominatim
except ImportError:
    Nominatim = None

_logger = logging.getLogger(__name__)


class HrAttendance(models.Model):
    """
    Model chấm công - Kế thừa từ Odoo 18 core hr.attendance
    Kết hợp tính năng từ NGSD và NGSC
    """
    _inherit = 'hr.attendance'
    
    # Work Location (from dropdown)
    work_location_id = fields.Many2one(
        'hr.work.location',
        string='Địa điểm làm việc',
        help='Địa điểm làm việc được chọn khi chấm công'
    )
    
    # GPS Check-in
    check_in_latitude = fields.Float(
        string='Check-in Vĩ độ',
        digits=(10, 7),
        readonly=True,
        help='Vĩ độ GPS khi check-in'
    )
    
    check_in_longitude = fields.Float(
        string='Check-in Kinh độ',
        digits=(10, 7),
        readonly=True,
        help='Kinh độ GPS khi check-in'
    )
    
    check_in_address = fields.Char(
        string='Địa chỉ Check-in',
        readonly=True,
        help='Địa chỉ được reverse từ GPS'
    )
    
    # GPS Check-out
    check_out_latitude = fields.Float(
        string='Check-out Vĩ độ',
        digits=(10, 7),
        readonly=True,
        help='Vĩ độ GPS khi check-out'
    )
    
    check_out_longitude = fields.Float(
        string='Check-out Kinh độ',
        digits=(10, 7),
        readonly=True,
        help='Kinh độ GPS khi check-out'
    )
    
    check_out_address = fields.Char(
        string='Địa chỉ Check-out',
        readonly=True,
        help='Địa chỉ được reverse từ GPS'
    )
    
    # Distance validation
    check_in_distance = fields.Float(
        string='Khoảng cách Check-in (m)',
        compute='_compute_distances',
        store=True,
        help='Khoảng cách từ vị trí check-in đến văn phòng'
    )
    
    check_out_distance = fields.Float(
        string='Khoảng cách Check-out (m)',
        compute='_compute_distances',
        store=True,
        help='Khoảng cách từ vị trí check-out đến văn phòng'
    )
    
    is_outside_radius = fields.Boolean(
        string='Ngoài bán kính',
        compute='_compute_distances',
        store=True,
        help='Chấm công ngoài bán kính cho phép'
    )
    
    # Computed display fields
    check_in_coordinates = fields.Char(
        string='Tọa độ Check-in',
        compute='_compute_coordinates_display',
        store=False
    )
    
    check_out_coordinates = fields.Char(
        string='Tọa độ Check-out',
        compute='_compute_coordinates_display',
        store=False
    )
    
    check_in_google_maps = fields.Char(
        string='Check-in Google Maps',
        compute='_compute_google_maps_urls',
        store=False
    )
    
    check_out_google_maps = fields.Char(
        string='Check-out Google Maps',
        compute='_compute_google_maps_urls',
        store=False
    )
    
    @api.depends('check_in_latitude', 'check_in_longitude', 'check_out_latitude', 'check_out_longitude')
    def _compute_coordinates_display(self):
        """Hiển thị tọa độ dạng text"""
        for record in self:
            if record.check_in_latitude and record.check_in_longitude:
                record.check_in_coordinates = f'{record.check_in_latitude:.6f}, {record.check_in_longitude:.6f}'
            else:
                record.check_in_coordinates = False
            
            if record.check_out_latitude and record.check_out_longitude:
                record.check_out_coordinates = f'{record.check_out_latitude:.6f}, {record.check_out_longitude:.6f}'
            else:
                record.check_out_coordinates = False
    
    @api.depends('check_in_latitude', 'check_in_longitude', 'check_out_latitude', 'check_out_longitude')
    def _compute_google_maps_urls(self):
        """Tạo link Google Maps"""
        for record in self:
            if record.check_in_latitude and record.check_in_longitude:
                record.check_in_google_maps = f'https://www.google.com/maps?q={record.check_in_latitude},{record.check_in_longitude}'
            else:
                record.check_in_google_maps = False
            
            if record.check_out_latitude and record.check_out_longitude:
                record.check_out_google_maps = f'https://www.google.com/maps?q={record.check_out_latitude},{record.check_out_longitude}'
            else:
                record.check_out_google_maps = False
    
    @api.depends('work_location_id', 'check_in_latitude', 'check_in_longitude', 
                 'check_out_latitude', 'check_out_longitude')
    def _compute_distances(self):
        """Tính khoảng cách từ vị trí chấm công đến văn phòng"""
        for record in self:
            check_in_dist = 0
            check_out_dist = 0
            outside = False
            
            if record.work_location_id and record.work_location_id.latitude and record.work_location_id.longitude:
                office_lat = record.work_location_id.latitude
                office_lon = record.work_location_id.longitude
                radius = record.work_location_id.radius or 500
                
                # Calculate check-in distance
                if record.check_in_latitude and record.check_in_longitude:
                    check_in_dist = self._calculate_distance(
                        office_lat, office_lon,
                        record.check_in_latitude, record.check_in_longitude
                    )
                    if check_in_dist > radius:
                        outside = True
                
                # Calculate check-out distance
                if record.check_out_latitude and record.check_out_longitude:
                    check_out_dist = self._calculate_distance(
                        office_lat, office_lon,
                        record.check_out_latitude, record.check_out_longitude
                    )
                    if check_out_dist > radius:
                        outside = True
            
            record.check_in_distance = check_in_dist
            record.check_out_distance = check_out_dist
            record.is_outside_radius = outside
    
    def _calculate_distance(self, lat1, lon1, lat2, lon2):
        """
        Tính khoảng cách giữa 2 điểm GPS (Haversine formula)
        Trả về khoảng cách tính bằng mét
        """
        # Radius của Trái Đất (km)
        R = 6371.0
        
        # Convert to radians
        lat1_rad = radians(lat1)
        lon1_rad = radians(lon1)
        lat2_rad = radians(lat2)
        lon2_rad = radians(lon2)
        
        # Differences
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        # Haversine formula
        a = sin(dlat / 2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        
        # Distance in meters
        distance = R * c * 1000
        
        return round(distance, 2)
    
    @api.model
    def _reverse_geocode(self, latitude, longitude):
        """
        Chuyển tọa độ GPS thành địa chỉ
        """
        if not Nominatim:
            _logger.warning('geopy not installed. Cannot reverse geocode.')
            return 'N/A'
        
        try:
            geolocator = Nominatim(user_agent="hdi_attendance")
            location = geolocator.reverse(f"{latitude}, {longitude}", language='vi')
            return location.address if location else 'N/A'
        except Exception as e:
            _logger.error(f'Error reverse geocoding: {e}')
            return 'N/A'
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create để xử lý GPS"""
        for vals in vals_list:
            # Reverse geocode if GPS provided
            if vals.get('check_in_latitude') and vals.get('check_in_longitude'):
                if not vals.get('check_in_address'):
                    vals['check_in_address'] = self._reverse_geocode(
                        vals['check_in_latitude'],
                        vals['check_in_longitude']
                    )
        
        return super().create(vals_list)
    
    def write(self, vals):
        """Override write để xử lý GPS check-out"""
        # Reverse geocode for check-out
        if vals.get('check_out_latitude') and vals.get('check_out_longitude'):
            if not vals.get('check_out_address'):
                vals['check_out_address'] = self._reverse_geocode(
                    vals['check_out_latitude'],
                    vals['check_out_longitude']
                )
        
        return super().write(vals)
    
    def action_view_check_in_map(self):
        """Xem vị trí check-in trên Google Maps"""
        self.ensure_one()
        if not self.check_in_google_maps:
            raise UserError(_('Không có tọa độ GPS cho check-in!'))
        
        return {
            'type': 'ir.actions.act_url',
            'url': self.check_in_google_maps,
            'target': 'new',
        }
    
    def action_view_check_out_map(self):
        """Xem vị trí check-out trên Google Maps"""
        self.ensure_one()
        if not self.check_out_google_maps:
            raise UserError(_('Không có tọa độ GPS cho check-out!'))
        
        return {
            'type': 'ir.actions.act_url',
            'url': self.check_out_google_maps,
            'target': 'new',
        }
