# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    # Geolocation settings
    attendance_geolocation_enabled = fields.Boolean(
        string='Bật định vị GPS',
        config_parameter='hdi_hr_attendance_enhanced.geolocation_enabled',
        default=True,
        help='Tự động lấy vị trí GPS khi chấm công'
    )
    
    attendance_geolocation_required = fields.Boolean(
        string='Bắt buộc GPS',
        config_parameter='hdi_hr_attendance_enhanced.geolocation_required',
        default=False,
        help='Bắt buộc phải có GPS mới cho phép chấm công'
    )
    
    # Queue settings
    attendance_queue_enabled = fields.Boolean(
        string='Bật Queue System',
        config_parameter='hdi_hr_attendance_enhanced.queue_enabled',
        default=True,
        help='Xử lý chấm công bất đồng bộ qua queue'
    )
    
    attendance_offline_mode = fields.Boolean(
        string='Cho phép Offline',
        config_parameter='hdi_hr_attendance_enhanced.offline_mode',
        default=True,
        help='Cho phép chấm công khi mất mạng (lưu localStorage)'
    )
    
    # Validation settings
    attendance_check_radius = fields.Boolean(
        string='Kiểm tra bán kính',
        config_parameter='hdi_hr_attendance_enhanced.check_radius',
        default=True,
        help='Cảnh báo khi chấm công ngoài bán kính cho phép'
    )
    
    attendance_default_radius = fields.Integer(
        string='Bán kính mặc định (m)',
        config_parameter='hdi_hr_attendance_enhanced.default_radius',
        default=500,
        help='Bán kính mặc định cho các địa điểm mới (đơn vị: mét)'
    )
