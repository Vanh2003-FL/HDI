# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    attendance_geolocation_enabled = fields.Boolean(
        string='Bật định vị GPS khi chấm công',
        config_parameter='hdi_hr_attendance_geolocation.enabled',
        default=True
    )
    
    attendance_geolocation_required = fields.Boolean(
        string='Bắt buộc GPS khi chấm công',
        config_parameter='hdi_hr_attendance_geolocation.required',
        help='Nếu bật, nhân viên phải cho phép truy cập vị trí mới có thể chấm công'
    )
    
    attendance_default_max_distance = fields.Float(
        string='Khoảng cách tối đa mặc định (km)',
        config_parameter='hdi_hr_attendance_geolocation.default_max_distance',
        default=0.5,
        help='Khoảng cách tối đa cho phép từ vị trí chấm công đến văn phòng'
    )
    
    attendance_location_timeout = fields.Integer(
        string='Timeout lấy vị trí (giây)',
        config_parameter='hdi_hr_attendance_geolocation.location_timeout',
        default=60,
        help='Thời gian chờ tối đa để lấy tọa độ GPS'
    )
    
    attendance_geocoding_enabled = fields.Boolean(
        string='Bật tra cứu địa chỉ',
        config_parameter='hdi_hr_attendance_geolocation.geocoding_enabled',
        default=True,
        help='Tự động tra cứu địa chỉ từ tọa độ GPS'
    )
