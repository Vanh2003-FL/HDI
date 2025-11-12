from odoo import *


class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    attendance_type = fields.Selection(string='Cách tính giờ làm', selection=[('actual', 'Thực tế'), ('not_ot', 'Không tăng ca'), ('fixed', 'Cố định')], required=True, default='actual', help="Để chọn cách tính giờ làm việc dựa trên Lịch làm việc và giờ chấm công của nhân viên\nThực tế: Tính theo khoảng thời gian thực từ thời điểm Check in đến Check out\nKhông tăng ca: Tính theo khoảng thời gian từ thời điểm Check in đến giờ check out theo Lịch làm việc\nCố định: Tính cố định bằng giờ làm việc cài đặt trong Lịch làm việc")
    round = fields.Integer(string='Làm tròn giờ làm', default=0)
    en_auto_checkout = fields.Boolean(string='Tự động check out', default=True, help='Lựa chọn cho phép hệ thống tự động ghi nhận thời gian check out cuối ngày nếu người dùng quên check out')

