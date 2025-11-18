# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'
    
    # HDI Calendar Extensions
    hdi_overtime_allowed = fields.Boolean(
        string='Cho phép tăng ca',
        default=True,
        help='Lịch làm việc này có cho phép tăng ca không'
    )
    
    hdi_max_overtime_hours = fields.Float(
        string='Số giờ tăng ca tối đa/ngày',
        default=4.0,
        help='Số giờ tăng ca tối đa trong một ngày'
    )
    
    hdi_break_time = fields.Float(
        string='Thời gian nghỉ giữa ca (giờ)',
        default=1.0,
        help='Thời gian nghỉ trưa hoặc nghỉ giữa ca'
    )


class ResourceCalendarAttendance(models.Model):
    _inherit = 'resource.calendar.attendance'
    
    # HDI Attendance Schedule Extensions
    hdi_flexible_time = fields.Boolean(
        string='Giờ linh hoạt',
        default=False,
        help='Ca làm việc này có thể linh hoạt giờ check in/out'
    )
    
    hdi_grace_period = fields.Integer(
        string='Thời gian ân hạn (phút)',
        default=15,
        help='Số phút ân hạn trước khi tính là đi muộn'
    )


# Work Entry extensions - will be enabled when hr_work_entry module is available
#
# class HrWorkEntry(models.Model):
#     _inherit = 'hr.work.entry'  # Comment out - hr_work_entry module may not be available
#    
#     # HDI Work Entry Extensions  
#     hdi_entry_type = fields.Selection([...], string='Loại công việc HDI')
#     hdi_bonus_rate = fields.Float(string='Hệ số thưởng')
#     hdi_approved_by = fields.Many2one('hr.employee', string='Người duyệt')
#
# class HrWorkEntryType(models.Model):
#     _inherit = 'hr.work.entry.type'  # Comment out - hr_work_entry module may not be available
#    
#     # HDI Work Entry Type Extensions
#     hdi_is_overtime = fields.Boolean(string='Là tăng ca')
#     hdi_overtime_rate = fields.Float(string='Hệ số tăng ca')
#     hdi_requires_approval = fields.Boolean(string='Cần duyệt trước')