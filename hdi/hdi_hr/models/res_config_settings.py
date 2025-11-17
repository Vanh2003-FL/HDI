# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    hdi_probation_period_days = fields.Integer(
        string='Thời gian thử việc (ngày)',
        default=60,
        config_parameter='hdi_hr.probation_period_days'
    )
    
    hdi_annual_leave_days = fields.Integer(
        string='Số ngày phép năm',
        default=12,
        config_parameter='hdi_hr.annual_leave_days'
    )
    
    hdi_enable_overtime = fields.Boolean(
        string='Cho phép tăng ca',
        default=True,
        config_parameter='hdi_hr.enable_overtime'
    )
    
    hdi_max_overtime_hours_per_day = fields.Float(
        string='Giờ tăng ca tối đa/ngày',
        default=4.0,
        config_parameter='hdi_hr.max_overtime_hours_per_day'
    )
