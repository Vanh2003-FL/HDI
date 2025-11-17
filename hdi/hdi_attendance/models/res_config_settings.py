# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Location settings
    hdi_enforce_location_checkin = fields.Boolean(
        related='company_id.hdi_enforce_location_checkin',
        readonly=False,
        string='Bắt buộc vị trí khi check-in'
    )
    
    hdi_enforce_location_checkout = fields.Boolean(
        related='company_id.hdi_enforce_location_checkout',
        readonly=False,
        string='Bắt buộc vị trí khi check-out'
    )
    
    hdi_max_checkin_distance = fields.Float(
        related='company_id.hdi_max_checkin_distance',
        readonly=False,
        string='Khoảng cách tối đa check-in (m)'
    )
    
    hdi_max_checkout_distance = fields.Float(
        related='company_id.hdi_max_checkout_distance',
        readonly=False,
        string='Khoảng cách tối đa check-out (m)'
    )
    
    # Time settings
    hdi_late_tolerance_minutes = fields.Integer(
        related='company_id.hdi_late_tolerance_minutes',
        readonly=False,
        string='Dung sai đi muộn (phút)'
    )
    
    hdi_early_leave_tolerance_minutes = fields.Integer(
        related='company_id.hdi_early_leave_tolerance_minutes',
        readonly=False,
        string='Dung sai về sớm (phút)'
    )
    
    hdi_auto_checkout_hours = fields.Float(
        related='company_id.hdi_auto_checkout_hours',
        readonly=False,
        string='Tự động check-out sau (giờ)'
    )
    
    # Working hours
    hdi_standard_working_hours = fields.Float(
        related='company_id.hdi_standard_working_hours',
        readonly=False,
        string='Giờ làm việc tiêu chuẩn/ngày'
    )
    
    hdi_overtime_threshold_hours = fields.Float(
        related='company_id.hdi_overtime_threshold_hours',
        readonly=False,
        string='Ngưỡng tăng ca (giờ)'
    )
    
    # Notifications
    hdi_notify_missing_checkin = fields.Boolean(
        related='company_id.hdi_notify_missing_checkin',
        readonly=False,
        string='Thông báo thiếu check-in'
    )
    
    hdi_notify_missing_checkout = fields.Boolean(
        related='company_id.hdi_notify_missing_checkout',
        readonly=False,
        string='Thông báo thiếu check-out'
    )
    
    hdi_notify_late_checkin = fields.Boolean(
        related='company_id.hdi_notify_late_checkin',
        readonly=False,
        string='Thông báo đi muộn'
    )


class ResCompany(models.Model):
    _inherit = 'res.company'

    # Location settings
    hdi_enforce_location_checkin = fields.Boolean(
        string='Bắt buộc vị trí khi check-in',
        default=True
    )
    
    hdi_enforce_location_checkout = fields.Boolean(
        string='Bắt buộc vị trí khi check-out',
        default=False
    )
    
    hdi_max_checkin_distance = fields.Float(
        string='Khoảng cách tối đa check-in (m)',
        default=100.0
    )
    
    hdi_max_checkout_distance = fields.Float(
        string='Khoảng cách tối đa check-out (m)',
        default=500.0
    )
    
    # Time settings
    hdi_late_tolerance_minutes = fields.Integer(
        string='Dung sai đi muộn (phút)',
        default=15
    )
    
    hdi_early_leave_tolerance_minutes = fields.Integer(
        string='Dung sai về sớm (phút)',
        default=15
    )
    
    hdi_auto_checkout_hours = fields.Float(
        string='Tự động check-out sau (giờ)',
        default=12.0
    )
    
    # Working hours
    hdi_standard_working_hours = fields.Float(
        string='Giờ làm việc tiêu chuẩn/ngày',
        default=8.0
    )
    
    hdi_overtime_threshold_hours = fields.Float(
        string='Ngưỡng tăng ca (giờ)',
        default=8.0
    )
    
    # Notifications
    hdi_notify_missing_checkin = fields.Boolean(
        string='Thông báo thiếu check-in',
        default=True
    )
    
    hdi_notify_missing_checkout = fields.Boolean(
        string='Thông báo thiếu check-out',
        default=True
    )
    
    hdi_notify_late_checkin = fields.Boolean(
        string='Thông báo đi muộn',
        default=True
    )