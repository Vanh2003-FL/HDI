# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import logging

_logger = logging.getLogger(__name__)


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    # GPS Coordinates
    check_in_latitude = fields.Float(
        string='Check-in Latitude',
        digits=(10, 7),
        readonly=True,
        help='Vĩ độ khi check-in'
    )
    
    check_in_longitude = fields.Float(
        string='Check-in Longitude',
        digits=(10, 7),
        readonly=True,
        help='Kinh độ khi check-in'
    )
    
    check_out_latitude = fields.Float(
        string='Check-out Latitude',
        digits=(10, 7),
        readonly=True,
        help='Vĩ độ khi check-out'
    )
    
    check_out_longitude = fields.Float(
        string='Check-out Longitude',
        digits=(10, 7),
        readonly=True,
        help='Kinh độ khi check-out'
    )
    
    # Formatted coordinates for display
    check_in_latitude_text = fields.Char(
        string='Check-in Vĩ độ (DMS)',
        compute='_compute_check_in_coordinates_text',
        store=True
    )
    
    check_in_longitude_text = fields.Char(
        string='Check-in Kinh độ (DMS)',
        compute='_compute_check_in_coordinates_text',
        store=True
    )
    
    check_out_latitude_text = fields.Char(
        string='Check-out Vĩ độ (DMS)',
        compute='_compute_check_out_coordinates_text',
        store=True
    )
    
    check_out_longitude_text = fields.Char(
        string='Check-out Kinh độ (DMS)',
        compute='_compute_check_out_coordinates_text',
        store=True
    )
    
    # Address information
    check_in_address = fields.Char(
        string='Địa chỉ Check-in',
        readonly=True,
        help='Địa chỉ chi tiết khi check-in'
    )
    
    check_out_address = fields.Char(
        string='Địa chỉ Check-out',
        readonly=True,
        help='Địa chỉ chi tiết khi check-out'
    )
    
    check_in_address_url = fields.Char(
        string='Link Google Maps Check-in',
        compute='_compute_address_urls',
        store=True,
        help='Link xem vị trí trên Google Maps'
    )
    
    check_out_address_url = fields.Char(
        string='Link Google Maps Check-out',
        compute='_compute_address_urls',
        store=True,
        help='Link xem vị trí trên Google Maps'
    )
    
    # Distance from office
    check_in_distance_from_office = fields.Float(
        string='Khoảng cách check-in (km)',
        compute='_compute_distance_from_office',
        store=True,
        help='Khoảng cách từ vị trí check-in đến văn phòng'
    )
    
    check_out_distance_from_office = fields.Float(
        string='Khoảng cách check-out (km)',
        compute='_compute_distance_from_office',
        store=True,
        help='Khoảng cách từ vị trí check-out đến văn phòng'
    )
    
    # Location validation
    is_check_in_valid_location = fields.Boolean(
        string='Vị trí Check-in hợp lệ',
        compute='_compute_location_validation',
        store=True
    )
    
    is_check_out_valid_location = fields.Boolean(
        string='Vị trí Check-out hợp lệ',
        compute='_compute_location_validation',
        store=True
    )
    
    location_warning = fields.Text(
        string='Cảnh báo vị trí',
        compute='_compute_location_validation',
        store=True
    )

    def _convert_decimal_to_dms(self, decimal_degree):
        """Chuyển đổi tọa độ thập phân sang độ phút giây (DMS)"""
        if not decimal_degree:
            return ''
        
        d = int(decimal_degree)
        m = int((decimal_degree - d) * 60)
        s = (decimal_degree - d - m / 60) * 3600.00
        
        return "%d° %d' %.2f\"" % (abs(d), abs(m), abs(s))

    def _format_latitude(self, latitude):
        """Format vĩ độ với hướng N/S"""
        if not latitude:
            return ''
        direction = 'N' if latitude >= 0 else 'S'
        return "%s %s" % (direction, self._convert_decimal_to_dms(latitude))

    def _format_longitude(self, longitude):
        """Format kinh độ với hướng E/W"""
        if not longitude:
            return ''
        direction = 'E' if longitude >= 0 else 'W'
        return "%s %s" % (direction, self._convert_decimal_to_dms(longitude))

    @api.depends('check_in_latitude', 'check_in_longitude')
    def _compute_check_in_coordinates_text(self):
        """Tính tọa độ check-in dạng text"""
        for record in self:
            record.check_in_latitude_text = self._format_latitude(record.check_in_latitude)
            record.check_in_longitude_text = self._format_longitude(record.check_in_longitude)

    @api.depends('check_out_latitude', 'check_out_longitude')
    def _compute_check_out_coordinates_text(self):
        """Tính tọa độ check-out dạng text"""
        for record in self:
            record.check_out_latitude_text = self._format_latitude(record.check_out_latitude)
            record.check_out_longitude_text = self._format_longitude(record.check_out_longitude)

    @api.depends('check_in_latitude', 'check_in_longitude', 'check_out_latitude', 'check_out_longitude')
    def _compute_address_urls(self):
        """Tạo link Google Maps"""
        for record in self:
            if record.check_in_latitude and record.check_in_longitude:
                record.check_in_address_url = "https://www.google.com/maps?q=%s,%s" % (
                    record.check_in_latitude,
                    record.check_in_longitude
                )
            else:
                record.check_in_address_url = ''
                
            if record.check_out_latitude and record.check_out_longitude:
                record.check_out_address_url = "https://www.google.com/maps?q=%s,%s" % (
                    record.check_out_latitude,
                    record.check_out_longitude
                )
            else:
                record.check_out_address_url = ''

    @api.depends('check_in_latitude', 'check_in_longitude', 
                 'check_out_latitude', 'check_out_longitude',
                 'employee_id.work_location_id')
    def _compute_distance_from_office(self):
        """Tính khoảng cách từ vị trí chấm công đến văn phòng"""
        for record in self:
            work_location = record.employee_id.work_location_id
            
            # Tính khoảng cách check-in
            if (record.check_in_latitude and record.check_in_longitude and 
                work_location and work_location.latitude and work_location.longitude):
                check_in_coords = (record.check_in_latitude, record.check_in_longitude)
                office_coords = (work_location.latitude, work_location.longitude)
                record.check_in_distance_from_office = geodesic(check_in_coords, office_coords).kilometers
            else:
                record.check_in_distance_from_office = 0.0
            
            # Tính khoảng cách check-out
            if (record.check_out_latitude and record.check_out_longitude and 
                work_location and work_location.latitude and work_location.longitude):
                check_out_coords = (record.check_out_latitude, record.check_out_longitude)
                office_coords = (work_location.latitude, work_location.longitude)
                record.check_out_distance_from_office = geodesic(check_out_coords, office_coords).kilometers
            else:
                record.check_out_distance_from_office = 0.0

    @api.depends('check_in_distance_from_office', 'check_out_distance_from_office',
                 'employee_id.work_location_id')
    def _compute_location_validation(self):
        """Kiểm tra vị trí chấm công có hợp lệ không"""
        for record in self:
            warnings = []
            work_location = record.employee_id.work_location_id
            
            if work_location and work_location.max_distance_allowed:
                max_distance = work_location.max_distance_allowed
                
                # Kiểm tra check-in
                if record.check_in_distance_from_office > max_distance:
                    record.is_check_in_valid_location = False
                    warnings.append(
                        _('Check-in: Cách văn phòng %.2f km (Cho phép: %.2f km)') % 
                        (record.check_in_distance_from_office, max_distance)
                    )
                else:
                    record.is_check_in_valid_location = True
                
                # Kiểm tra check-out
                if record.check_out_distance_from_office > max_distance:
                    record.is_check_out_valid_location = False
                    warnings.append(
                        _('Check-out: Cách văn phòng %.2f km (Cho phép: %.2f km)') % 
                        (record.check_out_distance_from_office, max_distance)
                    )
                else:
                    record.is_check_out_valid_location = True
            else:
                record.is_check_in_valid_location = True
                record.is_check_out_valid_location = True
            
            record.location_warning = '\n'.join(warnings) if warnings else ''

    def action_recompute_check_in_address(self):
        """Tính lại địa chỉ check-in từ tọa độ"""
        self.ensure_one()
        if not (self.check_in_latitude and self.check_in_longitude):
            raise UserError(_('Không có thông tin tọa độ check-in!'))
        
        try:
            geolocator = Nominatim(user_agent='hdi-hr-attendance')
            location = geolocator.reverse(
                "%s, %s" % (self.check_in_latitude, self.check_in_longitude),
                language='vi'
            )
            self.check_in_address = location.address if location else _('Không xác định được địa chỉ')
        except Exception as e:
            _logger.error("Error getting address for check-in: %s", e)
            raise UserError(_('Lỗi khi lấy địa chỉ: %s') % str(e))

    def action_recompute_check_out_address(self):
        """Tính lại địa chỉ check-out từ tọa độ"""
        self.ensure_one()
        if not (self.check_out_latitude and self.check_out_longitude):
            raise UserError(_('Không có thông tin tọa độ check-out!'))
        
        try:
            geolocator = Nominatim(user_agent='hdi-hr-attendance')
            location = geolocator.reverse(
                "%s, %s" % (self.check_out_latitude, self.check_out_longitude),
                language='vi'
            )
            self.check_out_address = location.address if location else _('Không xác định được địa chỉ')
        except Exception as e:
            _logger.error("Error getting address for check-out: %s", e)
            raise UserError(_('Lỗi khi lấy địa chỉ: %s') % str(e))

    def action_view_on_map(self):
        """Mở vị trí trên Google Maps"""
        self.ensure_one()
        if self.check_in_address_url:
            return {
                'type': 'ir.actions.act_url',
                'url': self.check_in_address_url,
                'target': 'new',
            }
        raise UserError(_('Không có thông tin vị trí!'))
