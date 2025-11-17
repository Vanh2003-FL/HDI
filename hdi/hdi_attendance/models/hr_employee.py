# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import pytz

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # Work location settings
    hdi_default_work_location_id = fields.Many2one(
        'hr.work.location',
        string='Địa điểm làm việc mặc định',
        help='Địa điểm làm việc mặc định của nhân viên'
    )
    
    hdi_allowed_work_locations = fields.Many2many(
        'hr.work.location',
        'employee_work_location_rel',
        'employee_id',
        'location_id',
        string='Địa điểm được phép làm việc',
        help='Các địa điểm mà nhân viên được phép check-in'
    )
    
    # Work shift settings
    hdi_default_work_shift = fields.Selection([
        ('morning', 'Ca sáng (6:00-14:00)'),
        ('afternoon', 'Ca chiều (14:00-22:00)'),
        ('night', 'Ca tối (22:00-6:00)'),
        ('full', 'Ca ngày (8:00-17:00)'),
        ('flexible', 'Ca linh hoạt'),
    ], string='Ca làm việc mặc định', default='full')
    
    # Attendance settings
    hdi_require_location_checkin = fields.Boolean(
        string='Bắt buộc vị trí khi check-in',
        default=True,
        help='Bắt buộc nhân viên phải ở gần địa điểm làm việc khi check-in'
    )
    
    hdi_require_location_checkout = fields.Boolean(
        string='Bắt buộc vị trí khi check-out',
        default=False,
        help='Bắt buộc nhân viên phải ở gần địa điểm làm việc khi check-out'
    )
    
    hdi_max_checkin_distance = fields.Float(
        string='Khoảng cách tối đa check-in (m)',
        default=100.0,
        help='Khoảng cách tối đa cho phép khi check-in (mét)'
    )
    
    hdi_max_checkout_distance = fields.Float(
        string='Khoảng cách tối đa check-out (m)',
        default=500.0,
        help='Khoảng cách tối đa cho phép khi check-out (mét)'
    )
    
    # Attendance statistics
    hdi_total_attendances = fields.Integer(
        string='Tổng số lần chấm công',
        compute='_compute_attendance_stats'
    )
    
    hdi_late_count = fields.Integer(
        string='Số lần đi muộn',
        compute='_compute_attendance_stats'
    )
    
    hdi_early_leave_count = fields.Integer(
        string='Số lần về sớm', 
        compute='_compute_attendance_stats'
    )
    
    hdi_missing_checkout_count = fields.Integer(
        string='Số lần thiếu check-out',
        compute='_compute_attendance_stats'
    )
    
    hdi_total_worked_hours = fields.Float(
        string='Tổng giờ làm việc',
        compute='_compute_attendance_stats'
    )
    
    hdi_total_overtime_hours = fields.Float(
        string='Tổng giờ làm thêm',
        compute='_compute_attendance_stats'
    )
    
    # Current attendance info
    hdi_last_checkin = fields.Datetime(
        string='Check-in gần nhất',
        compute='_compute_current_attendance_info'
    )
    
    hdi_current_work_location = fields.Many2one(
        'hr.work.location',
        string='Địa điểm hiện tại',
        compute='_compute_current_attendance_info'
    )

    @api.depends('attendance_ids')
    def _compute_attendance_stats(self):
        """Tính toán thống kê chấm công"""
        for employee in self:
            attendances = employee.attendance_ids
            employee.hdi_total_attendances = len(attendances)
            employee.hdi_late_count = len(attendances.filtered('hdi_is_late'))
            employee.hdi_early_leave_count = len(attendances.filtered('hdi_is_early_leave'))
            employee.hdi_missing_checkout_count = len(attendances.filtered('hdi_is_missing_checkout'))
            employee.hdi_total_worked_hours = sum(attendances.mapped('worked_hours'))
            employee.hdi_total_overtime_hours = sum(attendances.mapped('hdi_overtime_hours'))

    @api.depends('attendance_ids', 'attendance_state')
    def _compute_current_attendance_info(self):
        """Tính toán thông tin chấm công hiện tại"""
        for employee in self:
            if employee.attendance_state == 'checked_in':
                last_attendance = employee.attendance_ids.filtered(lambda a: not a.check_out)
                if last_attendance:
                    employee.hdi_last_checkin = last_attendance[0].check_in
                    employee.hdi_current_work_location = last_attendance[0].hdi_work_location_id
                else:
                    employee.hdi_last_checkin = False
                    employee.hdi_current_work_location = False
            else:
                employee.hdi_last_checkin = False
                employee.hdi_current_work_location = False

    def action_attendance_checkin(self):
        """Mở wizard check-in"""
        return {
            'name': _('Chấm công Check-in'),
            'type': 'ir.actions.act_window',
            'res_model': 'attendance.checkin.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_employee_id': self.id,
                'default_attendance_mode': 'check_in',
                'default_work_location_id': self.hdi_default_work_location_id.id,
            }
        }

    def action_attendance_checkout(self):
        """Mở wizard check-out"""
        return {
            'name': _('Chấm công Check-out'),
            'type': 'ir.actions.act_window',
            'res_model': 'attendance.checkin.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_employee_id': self.id,
                'default_attendance_mode': 'check_out',
            }
        }

    def action_view_attendances(self):
        """Xem danh sách chấm công của nhân viên"""
        return {
            'name': _('Chấm công của %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'hr.attendance',
            'view_mode': 'tree,form,calendar',
            'domain': [('employee_id', '=', self.id)],
            'context': {
                'search_default_employee_id': self.id,
                'default_employee_id': self.id,
            }
        }

    def action_attendance_dashboard(self):
        """Mở dashboard chấm công cá nhân"""
        return {
            'name': _('Dashboard chấm công - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'hr.attendance',
            'view_mode': 'kanban',
            'domain': [('employee_id', '=', self.id)],
            'context': {
                'search_default_employee_id': self.id,
                'group_by': 'check_in_date',
            }
        }

    @api.model
    def attendance_manual(self, employee_id, next_action, entered_pin=None):
        """Override attendance manual để add location tracking"""
        employee = self.browse(employee_id)
        if not employee:
            return False
            
        # Get attendance context
        context = self.env.context
        work_location_id = context.get('work_location_id')
        latitude = context.get('latitude')
        longitude = context.get('longitude')
        
        if next_action == 'check_in':
            # Validate location if required
            if employee.hdi_require_location_checkin and work_location_id:
                work_location = self.env['hr.work.location'].browse(work_location_id)
                if work_location and latitude and longitude:
                    distance = self._calculate_distance(
                        latitude, longitude,
                        work_location.latitude, work_location.longitude
                    )
                    if distance > employee.hdi_max_checkin_distance:
                        raise UserError(
                            _('Bạn đang ở quá xa địa điểm làm việc!\n'
                              'Khoảng cách: %.0f mét (Tối đa: %.0f mét)') %
                            (distance, employee.hdi_max_checkin_distance)
                        )
        
        # Call original method
        result = super().attendance_manual(employee_id, next_action, entered_pin)
        
        # Update attendance with location info
        if next_action in ['check_in', 'check_out']:
            last_attendance = employee.attendance_ids[0] if employee.attendance_ids else False
            if last_attendance:
                vals = {}
                if work_location_id:
                    if next_action == 'check_in':
                        vals['hdi_work_location_id'] = work_location_id
                    else:
                        vals['hdi_checkout_location_id'] = work_location_id
                
                if latitude and longitude:
                    if next_action == 'check_in':
                        vals.update({
                            'check_in_latitude': latitude,
                            'check_in_longitude': longitude,
                        })
                    else:
                        vals.update({
                            'check_out_latitude': latitude,
                            'check_out_longitude': longitude,
                        })
                
                if vals:
                    last_attendance.write(vals)
        
        return result

    def _calculate_distance(self, lat1, lon1, lat2, lon2):
        """Tính khoảng cách giữa 2 điểm GPS"""
        import math
        
        # Convert to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Earth radius in meters
        r = 6371000
        
        return r * c

    @api.onchange('hdi_default_work_location_id')
    def _onchange_default_work_location(self):
        """Auto add default work location to allowed locations"""
        if self.hdi_default_work_location_id:
            if self.hdi_default_work_location_id not in self.hdi_allowed_work_locations:
                self.hdi_allowed_work_locations = [(4, self.hdi_default_work_location_id.id)]

    def get_attendance_summary(self, date_from, date_to):
        """Lấy tóm tắt chấm công trong khoảng thời gian"""
        attendances = self.env['hr.attendance'].search([
            ('employee_id', '=', self.id),
            ('check_in_date', '>=', date_from),
            ('check_in_date', '<=', date_to),
        ])
        
        return {
            'total_days': len(set(attendances.mapped('check_in_date'))),
            'total_hours': sum(attendances.mapped('worked_hours')),
            'overtime_hours': sum(attendances.mapped('hdi_overtime_hours')),
            'late_count': len(attendances.filtered('hdi_is_late')),
            'early_leave_count': len(attendances.filtered('hdi_is_early_leave')),
            'missing_checkout_count': len(attendances.filtered('hdi_is_missing_checkout')),
            'explained_count': len(attendances.filtered('hdi_explanation_ids')),
        }

    def cron_check_missing_checkout(self):
        """Cron job kiểm tra thiếu check-out"""
        yesterday = fields.Date.today() - timedelta(days=1)
        
        missing_attendances = self.env['hr.attendance'].search([
            ('check_in_date', '=', yesterday),
            ('check_out', '=', False),
            ('hdi_is_missing_checkout', '=', False),
        ])
        
        for attendance in missing_attendances:
            attendance.hdi_is_missing_checkout = True
            attendance.message_post(
                body=_('Phát hiện thiếu check-out cho ngày %s') % yesterday,
                message_type='notification',
                subtype_xmlid='mail.mt_note'
            )