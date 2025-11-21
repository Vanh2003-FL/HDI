from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    en_max_distance = fields.Float("Khoảng cách chấm công tối đa", digits="Location", config_parameter="en_max_distance", default=0, help="Khoảng cách tối đa mà nhân viên có thể chấm công so với địa điểm làm việc đã chọn (giá trị 0 hiểu là không giới hạn khoảng cách).")
    group_en_checkout_location = fields.Boolean(string='Check out khác địa điểm', implied_group='ngs_attendance.group_en_checkout_location')
    en_max_attendance_request = fields.Float(string='Thời gian giải trình chấm công tối đa', config_parameter='en_max_attendance_request', default=0)
    en_max_attendance_request_count = fields.Integer(string='Số lần giải trình chấm công tối đa trong chu kỳ công', config_parameter='en_max_attendance_request_count', default=25)
    en_attendance_request_start = fields.Integer(string='Ngày bắt đầu chu kì công', config_parameter='en_attendance_request_start', default=3)
    en_late_request = fields.Float(string='Thời gian đi muộn', config_parameter='en_late_request', default=0)
    en_soon_request = fields.Float(string='Thời gian về sớm', config_parameter='en_soon_request', default=0)
    check_timesheet_before_checkout_hour = fields.Float(string='Thời gian log timesheet/ngày', config_parameter='check_timesheet_before_checkout_hour', default=0)
