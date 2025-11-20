# -*- coding: utf-8 -*-
from odoo import models, fields, api


class HrAttendanceLog(models.Model):
    _name = 'hr.attendance.log'
    _description = 'Attendance Log - Async Processing'
    _order = 'action_time desc'
    
    attendance_id = fields.Many2one('hr.attendance', string='Attendance', ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', string='Nhân viên', required=True)
    action_time = fields.Datetime(string='Thời gian', required=True, default=fields.Datetime.now)
    action_type = fields.Selection([
        ('check_in', 'Check In'),
        ('check_out', 'Check Out'),
    ], string='Loại hành động', required=True)
    status = fields.Selection([
        ('pending', 'Đang xử lý'),
        ('processed', 'Đã xử lý'),
        ('failed', 'Thất bại'),
    ], string='Trạng thái', default='pending', required=True)
    error_message = fields.Text(string='Thông báo lỗi')
    
    @api.model
    def cron_process_pending_logs(self):
        """Cron job to process pending attendance logs"""
        pending_logs = self.search([('status', '=', 'pending')], limit=100)
        
        for log in pending_logs:
            try:
                # Process the log
                if log.action_type == 'check_in':
                    # Create attendance record
                    attendance = self.env['hr.attendance'].create({
                        'employee_id': log.employee_id.id,
                        'check_in': log.action_time,
                    })
                    log.write({
                        'attendance_id': attendance.id,
                        'status': 'processed',
                    })
                elif log.action_type == 'check_out' and log.attendance_id:
                    # Update attendance record
                    log.attendance_id.write({
                        'check_out': log.action_time,
                    })
                    log.status = 'processed'
                    
            except Exception as e:
                log.write({
                    'status': 'failed',
                    'error_message': str(e),
                })
