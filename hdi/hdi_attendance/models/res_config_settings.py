# -*- coding: utf-8 -*-
from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    attendance_require_geolocation = fields.Boolean(
        string='Yêu cầu định vị GPS khi chấm công',
        config_parameter='hdi_attendance.require_geolocation',
    )
    
    attendance_allow_manual_checkin = fields.Boolean(
        string='Cho phép chấm công thủ công',
        config_parameter='hdi_attendance.allow_manual_checkin',
        default=True,
    )
    
    attendance_explanation_required_days = fields.Integer(
        string='Số ngày yêu cầu giải trình',
        config_parameter='hdi_attendance.explanation_required_days',
        default=7,
        help='Số ngày tối đa để tạo giải trình chấm công cho các ngày quá khứ',
    )
