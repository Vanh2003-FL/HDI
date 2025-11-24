# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from geopy.geocoders import Nominatim
import logging

_logger = logging.getLogger(__name__)


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    work_location_id = fields.Many2one(
        'hr.work.location',
        string='Vị trí làm việc',
        help='Văn phòng/địa điểm làm việc chính của nhân viên'
    )

    allow_remote_attendance = fields.Boolean(
        string='Cho phép chấm công từ xa',
        default=False,
        help='Nếu bật, nhân viên có thể chấm công ở bất kỳ đâu'
    )

    def attendance_action_change(self):
        """Public method to handle attendance check-in/out with GPS"""
        self.ensure_one()
        return self._attendance_action_change()

    def _attendance_action_change(self, geo_ip_response=None):
        """Override để lưu thông tin GPS khi check-in/check-out"""
        result = super()._attendance_action_change(geo_ip_response)

        # Lấy tọa độ GPS từ context (được gửi từ JavaScript)
        latitude = self.env.context.get('latitude')
        longitude = self.env.context.get('longitude')

        if not latitude or not longitude:
            _logger.warning("No GPS coordinates provided for attendance of employee %s", self.name)
            return result

        # Lấy bản ghi attendance vừa tạo/cập nhật
        attendance = self.env['hr.attendance'].search([
            ('employee_id', '=', self.id)
        ], order='id desc', limit=1)

        if not attendance:
            return result

        try:
            # Lấy địa chỉ từ tọa độ
            geolocator = Nominatim(user_agent='hdi-hr-attendance', timeout=10)
            location = geolocator.reverse(
                "%s, %s" % (latitude, longitude),
                language='vi'
            )
            address = location.address if location else _('Không xác định được địa chỉ')

            # Cập nhật thông tin GPS và địa chỉ
            if self.attendance_state == 'checked_in':
                # Vừa check-in
                attendance.write({
                    'check_in_latitude': latitude,
                    'check_in_longitude': longitude,
                    'check_in_address': address,
                })
                _logger.info(
                    "Check-in location saved for %s: %s (%s, %s)",
                    self.name, address, latitude, longitude
                )
            else:
                # Vừa check-out
                attendance.write({
                    'check_out_latitude': latitude,
                    'check_out_longitude': longitude,
                    'check_out_address': address,
                })
                _logger.info(
                    "Check-out location saved for %s: %s (%s, %s)",
                    self.name, address, latitude, longitude
                )

            # Kiểm tra vị trí và cảnh báo nếu cần
            if not self.allow_remote_attendance and attendance.location_warning:
                # Có thể gửi thông báo hoặc log warning
                _logger.warning(
                    "Location warning for %s: %s",
                    self.name, attendance.location_warning
                )

        except Exception as e:
            _logger.error("Error processing geolocation for employee %s: %s", self.name, e)
            # Vẫn lưu tọa độ ngay cả khi không lấy được địa chỉ
            if self.attendance_state == 'checked_in':
                attendance.write({
                    'check_in_latitude': latitude,
                    'check_in_longitude': longitude,
                    'check_in_address': _('Lỗi lấy địa chỉ: %s') % str(e),
                })
            else:
                attendance.write({
                    'check_out_latitude': latitude,
                    'check_out_longitude': longitude,
                    'check_out_address': _('Lỗi lấy địa chỉ: %s') % str(e),
                })

        return result
