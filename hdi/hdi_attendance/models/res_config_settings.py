# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    # Distance settings
    en_max_distance = fields.Float(
        string='Khoảng cách chấm công tối đa (km)',
        config_parameter='en_max_distance',
        default=0.0,
        help='Khoảng cách tối đa mà nhân viên có thể chấm công so với địa điểm làm việc (0 = không giới hạn)'
    )
    
    # Explanation settings
    en_max_attendance_request = fields.Float(
        string='Thời gian giải trình tối đa (giờ)',
        config_parameter='en_max_attendance_request',
        default=720.0,
        help='Số giờ tối đa sau khi check out mà nhân viên có thể tạo giải trình (720 = 30 ngày)'
    )
    
    en_max_attendance_request_count = fields.Integer(
        string='Số lần giải trình tối đa/chu kỳ',
        config_parameter='en_max_attendance_request_count',
        default=3,
        help='Số lần giải trình chấm công tối đa trong một chu kỳ công'
    )
    
    en_attendance_request_start = fields.Integer(
        string='Ngày bắt đầu chu kỳ công',
        config_parameter='en_attendance_request_start',
        default=25,
        help='Ngày bắt đầu chu kỳ tính công trong tháng (VD: 25 = từ ngày 25 tháng trước đến 24 tháng sau)'
    )
    
    # Late/Soon tolerance
    en_late_request = fields.Float(
        string='Dung sai đi muộn (giờ)',
        config_parameter='en_late_request',
        default=0.25,
        help='Số giờ dung sai để tính là đi muộn (0.25 = 15 phút)'
    )
    
    en_soon_request = fields.Float(
        string='Dung sai về sớm (giờ)',
        config_parameter='en_soon_request',
        default=0.25,
        help='Số giờ dung sai để tính là về sớm (0.25 = 15 phút)'
    )
