# -*- coding: utf-8 -*-
from datetime import datetime
import pytz

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AttendanceCheckinWizard(models.TransientModel):
    _name = 'attendance.checkin.wizard'
    _description = 'Wizard chấm công Check-in/Check-out'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Nhân viên',
        required=True,
        default=lambda self: self.env.user.employee_id
    )
    
    attendance_mode = fields.Selection([
        ('check_in', 'Check In'),
        ('check_out', 'Check Out')
    ], string='Loại chấm công', required=True, default='check_in')
    
    work_location_id = fields.Many2one(
        'hr.work.location',
        string='Địa điểm làm việc',
        help='Chọn địa điểm làm việc'
    )
    
    work_shift = fields.Selection([
        ('morning', 'Ca sáng (6:00-14:00)'),
        ('afternoon', 'Ca chiều (14:00-22:00)'),
        ('night', 'Ca tối (22:00-6:00)'),
        ('full', 'Ca ngày (8:00-17:00)'),
        ('flexible', 'Ca linh hoạt'),
    ], string='Ca làm việc', default='full')
    
    # GPS fields
    latitude = fields.Float(
        string='Vĩ độ',
        digits=(10, 7)
    )
    
    longitude = fields.Float(
        string='Kinh độ',
        digits=(10, 7)
    )
    
    # Current attendance info
    current_attendance_id = fields.Many2one(
        'hr.attendance',
        string='Chấm công hiện tại',
        readonly=True
    )
    
    last_checkin_info = fields.Text(
        string='Thông tin check-in gần nhất',
        readonly=True
    )
    
    # Status fields
    can_check_in = fields.Boolean(
        string='Có thể check-in',
        compute='_compute_can_check',
        readonly=True
    )
    
    can_check_out = fields.Boolean(
        string='Có thể check-out',
        compute='_compute_can_check',
        readonly=True
    )
    
    distance_to_location = fields.Float(
        string='Khoảng cách đến địa điểm (m)',
        compute='_compute_distance',
        readonly=True
    )
    
    location_warning = fields.Text(
        string='Cảnh báo vị trí',
        compute='_compute_distance',
        readonly=True
    )
    
    note = fields.Text(
        string='Ghi chú',
        help='Ghi chú thêm về chấm công (nếu cần)'
    )

    @api.depends('employee_id', 'attendance_mode')
    def _compute_can_check(self):
        """Kiểm tra xem có thể check in/out không"""
        for wizard in self:
            wizard.can_check_in = False
            wizard.can_check_out = False
            
            if not wizard.employee_id:
                continue
                
            if wizard.attendance_mode == 'check_in':
                wizard.can_check_in = wizard.employee_id.attendance_state == 'checked_out'
            else:
                wizard.can_check_out = wizard.employee_id.attendance_state == 'checked_in'

    @api.depends('latitude', 'longitude', 'work_location_id', 'employee_id')
    def _compute_distance(self):
        """Tính khoảng cách và cảnh báo vị trí"""
        for wizard in self:
            wizard.distance_to_location = 0.0
            wizard.location_warning = ""
            
            if not (wizard.latitude and wizard.longitude and wizard.work_location_id):
                continue
                
            # Calculate distance
            distance = wizard.work_location_id.get_distance_from(
                wizard.latitude, wizard.longitude
            )
            wizard.distance_to_location = distance
            
            # Check location requirements
            settings = self.env['attendance.settings'].get_settings()
            
            if wizard.attendance_mode == 'check_in':
                if settings.enforce_location_checkin and distance > settings.max_checkin_distance:
                    wizard.location_warning = _(
                        'Bạn đang ở quá xa địa điểm làm việc! '
                        'Khoảng cách: %.0f mét (Tối đa: %.0f mét)'
                    ) % (distance, settings.max_checkin_distance)
            else:
                if settings.enforce_location_checkout and distance > settings.max_checkout_distance:
                    wizard.location_warning = _(
                        'Bạn đang ở quá xa địa điểm làm việc! '
                        'Khoảng cách: %.0f mét (Tối đa: %.0f mét)'
                    ) % (distance, settings.max_checkout_distance)

    @api.depends('employee_id')
    def _compute_last_attendance_info(self):
        """Hiển thị thông tin chấm công gần nhất"""
        for wizard in self:
            wizard.last_checkin_info = ""
            
            if not wizard.employee_id:
                continue
                
            last_attendance = wizard.employee_id.attendance_ids[:1]
            if last_attendance:
                if last_attendance.check_out:
                    wizard.last_checkin_info = _(
                        'Check-out gần nhất: %s lúc %s'
                    ) % (
                        last_attendance.check_out_date,
                        last_attendance.check_out.strftime('%H:%M:%S')
                    )
                else:
                    wizard.last_checkin_info = _(
                        'Đang check-in từ %s lúc %s'
                    ) % (
                        last_attendance.check_in_date,
                        last_attendance.check_in.strftime('%H:%M:%S')
                    )
                    wizard.current_attendance_id = last_attendance

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        """Tự động set địa điểm và ca làm việc mặc định"""
        if self.employee_id:
            self.work_location_id = self.employee_id.hdi_default_work_location_id
            self.work_shift = self.employee_id.hdi_default_work_shift
            
            # Set allowed work locations domain
            allowed_locations = self.employee_id.hdi_allowed_work_locations
            if allowed_locations:
                return {
                    'domain': {
                        'work_location_id': [('id', 'in', allowed_locations.ids)]
                    }
                }

    @api.onchange('attendance_mode')
    def _onchange_attendance_mode(self):
        """Cập nhật current_attendance_id khi đổi mode"""
        if self.attendance_mode == 'check_out':
            if self.employee_id and self.employee_id.attendance_state == 'checked_in':
                last_attendance = self.employee_id.attendance_ids.filtered(lambda a: not a.check_out)[:1]
                self.current_attendance_id = last_attendance
        else:
            self.current_attendance_id = False

    def action_check_in(self):
        """Thực hiện Check In"""
        self.ensure_one()
        
        if not self.can_check_in:
            raise UserError(_('Bạn đã Check In rồi! Vui lòng Check Out trước khi Check In lại.'))
        
        if not self.work_location_id:
            raise UserError(_('Vui lòng chọn địa điểm làm việc!'))
        
        # Validate location if required
        if self.location_warning:
            settings = self.env['attendance.settings'].get_settings()
            if settings.enforce_location_checkin:
                raise UserError(self.location_warning)
        
        # Prepare attendance values
        vals = {
            'employee_id': self.employee_id.id,
            'check_in': fields.Datetime.now(),
            'hdi_work_location_id': self.work_location_id.id,
            'hdi_work_shift': self.work_shift,
        }
        
        # Add GPS data if available
        if self.latitude and self.longitude:
            vals.update({
                'check_in_latitude': self.latitude,
                'check_in_longitude': self.longitude,
            })
        
        if self.note:
            vals['note'] = self.note
        
        # Create attendance record
        try:
            attendance = self.env['hr.attendance'].create(vals)
            
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
                        self.work_location_id.name
                    ),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            raise UserError(_('Không thể Check In: %s') % str(e))

    def action_check_out(self):
        """Thực hiện Check Out"""
        self.ensure_one()
        
        if not self.can_check_out:
            raise UserError(_('Bạn chưa Check In! Vui lòng Check In trước khi Check Out.'))
        
        if not self.current_attendance_id:
            raise UserError(_('Không tìm thấy bản ghi Check In!'))
        
        # Validate location if required
        if self.location_warning:
            settings = self.env['attendance.settings'].get_settings()
            if settings.enforce_location_checkout:
                raise UserError(self.location_warning)
        
        # Prepare values
        vals = {
            'check_out': fields.Datetime.now(),
        }
        
        # Add checkout location and GPS if provided
        if self.work_location_id:
            vals['hdi_checkout_location_id'] = self.work_location_id.id
            
        if self.latitude and self.longitude:
            vals.update({
                'check_out_latitude': self.latitude,
                'check_out_longitude': self.longitude,
            })
        
        if self.note:
            if self.current_attendance_id.note:
                vals['note'] = self.current_attendance_id.note + '\n' + self.note
            else:
                vals['note'] = self.note
        
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
            raise UserError(_('Không thể Check Out: %s') % str(e))

    def action_process(self):
        """Xử lý Check In/Out dựa vào mode"""
        if self.attendance_mode == 'check_in':
            return self.action_check_in()
        else:
            return self.action_check_out()

    def action_get_location(self):
        """Action để lấy vị trí GPS (sẽ được handle bởi JavaScript)"""
        return {
            'type': 'ir.actions.client',
            'tag': 'get_gps_location',
            'params': {
                'wizard_id': self.id,
            }
        }

    @api.model
    def update_location(self, wizard_id, latitude, longitude):
        """Cập nhật vị trí GPS từ JavaScript"""
        wizard = self.browse(wizard_id)
        if wizard:
            wizard.write({
                'latitude': latitude,
                'longitude': longitude,
            })
        return True