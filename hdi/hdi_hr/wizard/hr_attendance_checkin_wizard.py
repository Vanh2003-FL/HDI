# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
import pytz
import logging

_logger = logging.getLogger(__name__)


class HrAttendanceCheckinWizard(models.TransientModel):
    _name = 'hr.attendance.checkin.wizard'
    _description = 'Wizard Chấm công Check In/Check Out'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Nhân viên',
        required=True,
        readonly=True,
        default=lambda self: self.env.user.employee_id
    )
    
    work_location_id = fields.Many2one(
        'hr.work.location',
        string='Địa điểm làm việc',
        required=True,
        help='Chọn địa điểm làm việc của bạn'
    )
    
    attendance_mode = fields.Selection([
        ('check_in', 'Check In'),
        ('check_out', 'Check Out')
    ], string='Loại', required=True, default='check_in')
    
    current_attendance_id = fields.Many2one(
        'hr.attendance',
        string='Chấm công hiện tại',
        readonly=True
    )
    
    # GPS fields (optional - only if geolocation module installed)
    latitude = fields.Float(
        string='Vĩ độ',
        digits=(10, 7),
        help='Nhập vĩ độ GPS hoặc để trống nếu làm từ xa'
    )
    
    longitude = fields.Float(
        string='Kinh độ',
        digits=(10, 7),
        help='Nhập kinh độ GPS hoặc để trống nếu làm từ xa'
    )
    
    # Display information
    last_attendance_info = fields.Char(
        string='Chấm công gần nhất',
        compute='_compute_last_attendance_info',
        readonly=True
    )
    
    can_check_in = fields.Boolean(
        string='Có thể Check In',
        compute='_compute_can_check',
        readonly=True
    )
    
    can_check_out = fields.Boolean(
        string='Có thể Check Out',
        compute='_compute_can_check',
        readonly=True
    )
    
    note = fields.Text(
        string='Ghi chú',
        help='Ghi chú thêm về chấm công (nếu cần)'
    )

    @api.depends('employee_id')
    def _compute_can_check(self):
        """Kiểm tra xem nhân viên có thể check in/out không"""
        for wizard in self:
            if not wizard.employee_id:
                wizard.can_check_in = False
                wizard.can_check_out = False
                continue
            
            last_attendance = self.env['hr.attendance'].search([
                ('employee_id', '=', wizard.employee_id.id),
            ], order='check_in desc', limit=1)
            
            wizard.can_check_in = not last_attendance or last_attendance.check_out
            wizard.can_check_out = last_attendance and not last_attendance.check_out
            
            if wizard.can_check_out:
                wizard.current_attendance_id = last_attendance
            else:
                wizard.current_attendance_id = False

    @api.depends('employee_id')
    def _compute_last_attendance_info(self):
        """Hiển thị thông tin chấm công gần nhất"""
        for wizard in self:
            if not wizard.employee_id:
                wizard.last_attendance_info = ''
                continue
            
            last_attendance = self.env['hr.attendance'].search([
                ('employee_id', '=', wizard.employee_id.id),
            ], order='check_in desc', limit=1)
            
            if not last_attendance:
                wizard.last_attendance_info = 'Chưa có lịch sử chấm công'
            elif last_attendance.check_out:
                tz = pytz.timezone(wizard.employee_id.tz or 'Asia/Ho_Chi_Minh')
                check_out_local = pytz.utc.localize(last_attendance.check_out).astimezone(tz)
                wizard.last_attendance_info = 'Check Out lúc: %s' % check_out_local.strftime('%d/%m/%Y %H:%M:%S')
            else:
                tz = pytz.timezone(wizard.employee_id.tz or 'Asia/Ho_Chi_Minh')
                check_in_local = pytz.utc.localize(last_attendance.check_in).astimezone(tz)
                wizard.last_attendance_info = 'Đang Check In từ: %s' % check_in_local.strftime('%d/%m/%Y %H:%M:%S')

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        """Tự động set địa điểm làm việc mặc định của nhân viên"""
        if self.employee_id and self.employee_id.work_location_id:
            self.work_location_id = self.employee_id.work_location_id

    @api.onchange('attendance_mode')
    def _onchange_attendance_mode(self):
        """Cập nhật current_attendance_id khi đổi mode"""
        self._compute_can_check()

    def action_check_in(self):
        """Thực hiện Check In"""
        self.ensure_one()
        
        if not self.can_check_in:
            raise UserError(_('Bạn đã Check In rồi! Vui lòng Check Out trước khi Check In lại.'))
        
        # Prepare values
        vals = {
            'employee_id': self.employee_id.id,
            'check_in': fields.Datetime.now(),
        }
        
        # Add GPS data if available (only if geolocation module installed)
        if self.latitude and self.longitude:
            vals.update({
                'check_in_latitude': self.latitude,
                'check_in_longitude': self.longitude,
            })
        
        # Create attendance
        try:
            attendance = self.env['hr.attendance'].create(vals)
            
            # Update work location if needed
            if self.work_location_id and self.employee_id.work_location_id != self.work_location_id:
                self.employee_id.work_location_id = self.work_location_id
            
            # Show success message
            tz = pytz.timezone(self.employee_id.tz or 'Asia/Ho_Chi_Minh')
            check_in_local = pytz.utc.localize(attendance.check_in).astimezone(tz)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Check In thành công!'),
                    'message': _('Bạn đã Check In lúc %s tại %s') % (
                        check_in_local.strftime('%H:%M:%S'),
                        self.work_location_id.name or 'Địa điểm làm việc'
                    ),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            _logger.error('Error during check in: %s', str(e))
            raise UserError(_('Không thể Check In: %s') % str(e))

    def action_check_out(self):
        """Thực hiện Check Out"""
        self.ensure_one()
        
        if not self.can_check_out:
            raise UserError(_('Bạn chưa Check In! Vui lòng Check In trước khi Check Out.'))
        
        if not self.current_attendance_id:
            raise UserError(_('Không tìm thấy bản ghi Check In!'))
        
        # Prepare values
        vals = {
            'check_out': fields.Datetime.now(),
        }
        
        # Add GPS data if available (only if geolocation module installed)
        if self.latitude and self.longitude:
            vals.update({
                'check_out_latitude': self.latitude,
                'check_out_longitude': self.longitude,
            })
        
        # Update attendance
        try:
            self.current_attendance_id.write(vals)
            
            # Show success message
            tz = pytz.timezone(self.employee_id.tz or 'Asia/Ho_Chi_Minh')
            check_out_local = pytz.utc.localize(self.current_attendance_id.check_out).astimezone(tz)
            worked_hours = self.current_attendance_id.worked_hours
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Check Out thành công!'),
                    'message': _('Bạn đã Check Out lúc %s. Tổng giờ làm: %.2f giờ') % (
                        check_out_local.strftime('%H:%M:%S'),
                        worked_hours
                    ),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            _logger.error('Error during check out: %s', str(e))
            raise UserError(_('Không thể Check Out: %s') % str(e))

    def action_process(self):
        """Xử lý Check In/Out dựa vào mode"""
        self.ensure_one()
        
        if self.attendance_mode == 'check_in':
            return self.action_check_in()
        else:
            return self.action_check_out()
