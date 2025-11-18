# -*- coding: utf-8 -*-

import logging
from odoo import http, fields, _
from odoo.http import request
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class HrAttendanceController(http.Controller):
    """
    Controller xử lý attendance log từ frontend
    Tương tự NGSC controller nhưng cải tiến hơn
    """
    
    @http.route('/hr_attendance/log', type='json', auth='user', methods=['POST'], csrf=False)
    def create_attendance_log(self, **data):
        """
        API để tạo log chấm công từ frontend
        
        Params:
            - employee_id: ID nhân viên
            - action: 'check_in' hoặc 'check_out'
            - timestamp: Thời gian (ISO format)
            - latitude: Vĩ độ GPS (optional)
            - longitude: Kinh độ GPS (optional)
            - work_location_id: ID địa điểm (optional)
        
        Returns:
            {
                'success': True/False,
                'log_id': ID của log được tạo,
                'message': Thông báo
            }
        """
        try:
            employee_id = data.get('employee_id')
            action = data.get('action')
            timestamp = data.get('timestamp') or fields.Datetime.now()
            latitude = data.get('latitude')
            longitude = data.get('longitude')
            work_location_id = data.get('work_location_id')
            
            # Validate
            if not employee_id:
                return {
                    'success': False,
                    'error': 'missing_employee',
                    'message': _('Không tìm thấy thông tin nhân viên')
                }
            
            if action not in ('check_in', 'check_out'):
                return {
                    'success': False,
                    'error': 'invalid_action',
                    'message': _('Hành động không hợp lệ')
                }
            
            # Check if queue enabled
            queue_enabled = request.env['ir.config_parameter'].sudo().get_param(
                'hdi_hr_attendance_enhanced.queue_enabled', 'True'
            )
            
            if queue_enabled == 'True':
                # Create log for async processing
                vals = {
                    'employee_id': int(employee_id),
                    'action': action,
                    'timestamp': timestamp,
                }
                
                if latitude and longitude:
                    vals.update({
                        'latitude': float(latitude),
                        'longitude': float(longitude),
                    })
                
                if work_location_id:
                    vals['work_location_id'] = int(work_location_id)
                
                log = request.env['hr.attendance.log'].sudo().create(vals)
                
                # Auto-process if immediate processing enabled
                auto_process = request.env['ir.config_parameter'].sudo().get_param(
                    'hdi_hr_attendance_enhanced.auto_process', 'True'
                )
                
                if auto_process == 'True':
                    try:
                        log.action_process()
                    except Exception as e:
                        _logger.error(f'Auto-process failed: {e}')
                        # Still return success since log is created
                
                return {
                    'success': True,
                    'log_id': log.id,
                    'message': _('Đã ghi nhận chấm công của bạn!'),
                    'action': action,
                    'timestamp': timestamp,
                }
            else:
                # Direct create attendance (legacy mode)
                vals = {
                    'employee_id': int(employee_id),
                }
                
                if latitude and longitude:
                    if action == 'check_in':
                        vals.update({
                            'check_in': timestamp,
                            'check_in_latitude': float(latitude),
                            'check_in_longitude': float(longitude),
                        })
                    else:
                        vals.update({
                            'check_out': timestamp,
                            'check_out_latitude': float(latitude),
                            'check_out_longitude': float(longitude),
                        })
                
                if work_location_id:
                    vals['work_location_id'] = int(work_location_id)
                
                if action == 'check_in':
                    vals['check_in'] = timestamp
                    attendance = request.env['hr.attendance'].sudo().create(vals)
                else:
                    # Find last attendance
                    last = request.env['hr.attendance'].sudo().search([
                        ('employee_id', '=', int(employee_id)),
                        ('check_out', '=', False)
                    ], limit=1, order='check_in desc')
                    
                    if not last:
                        return {
                            'success': False,
                            'error': 'no_checkin',
                            'message': _('Bạn chưa check-in!')
                        }
                    
                    update_vals = {'check_out': timestamp}
                    if latitude and longitude:
                        update_vals.update({
                            'check_out_latitude': float(latitude),
                            'check_out_longitude': float(longitude),
                        })
                    
                    last.write(update_vals)
                    attendance = last
                
                return {
                    'success': True,
                    'attendance_id': attendance.id,
                    'message': _('Chấm công thành công!'),
                    'action': action,
                }
                
        except ValidationError as e:
            return {
                'success': False,
                'error': 'validation_error',
                'message': str(e)
            }
        except Exception as e:
            _logger.exception('Error creating attendance log: %s', e)
            return {
                'success': False,
                'error': 'server_error',
                'message': _('Lỗi hệ thống. Vui lòng thử lại sau.')
            }
    
    @http.route('/hr_attendance/get_locations', type='json', auth='user')
    def get_work_locations(self):
        """
        API lấy danh sách địa điểm cho dropdown
        """
        try:
            employee = request.env.user.employee_id
            if not employee:
                return {'success': False, 'error': 'no_employee'}
            
            result = employee.get_available_work_locations()
            result['success'] = True
            return result
            
        except Exception as e:
            _logger.error(f'Error getting locations: {e}')
            return {
                'success': False,
                'error': str(e)
            }
    
    @http.route('/hr_attendance/check_settings', type='json', auth='user')
    def check_settings(self):
        """
        API kiểm tra các settings
        """
        try:
            ICP = request.env['ir.config_parameter'].sudo()
            
            return {
                'success': True,
                'geolocation_enabled': ICP.get_param('hdi_hr_attendance_enhanced.geolocation_enabled', 'True') == 'True',
                'geolocation_required': ICP.get_param('hdi_hr_attendance_enhanced.geolocation_required', 'False') == 'True',
                'queue_enabled': ICP.get_param('hdi_hr_attendance_enhanced.queue_enabled', 'True') == 'True',
                'offline_mode': ICP.get_param('hdi_hr_attendance_enhanced.offline_mode', 'True') == 'True',
                'check_radius': ICP.get_param('hdi_hr_attendance_enhanced.check_radius', 'True') == 'True',
            }
        except Exception as e:
            _logger.error(f'Error checking settings: {e}')
            return {
                'success': False,
                'error': str(e)
            }
