# -*- coding: utf-8 -*-

import logging
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class HrAttendanceLog(models.Model):
    """
    Queue system cho chấm công bất đồng bộ
    Kế thừa ý tưởng từ NGSC ngs_hr_attendance_async
    """
    _name = 'hr.attendance.log'
    _description = 'Attendance Queue Log'
    _order = 'create_date desc'
    
    employee_id = fields.Many2one(
        'hr.employee',
        string='Nhân viên',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    action = fields.Selection(
        [
            ('check_in', 'Check In'),
            ('check_out', 'Check Out')
        ],
        string='Hành động',
        required=True
    )
    
    timestamp = fields.Datetime(
        string='Thời gian',
        required=True,
        default=fields.Datetime.now,
        index=True
    )
    
    state = fields.Selection(
        [
            ('pending', 'Chờ xử lý'),
            ('processing', 'Đang xử lý'),
            ('processed', 'Đã xử lý'),
            ('rejected', 'Bị từ chối'),
            ('failed', 'Thất bại'),
        ],
        string='Trạng thái',
        default='pending',
        required=True,
        index=True
    )
    
    # GPS data from client
    latitude = fields.Float(
        string='Vĩ độ',
        digits=(10, 7)
    )
    
    longitude = fields.Float(
        string='Kinh độ',
        digits=(10, 7)
    )
    
    work_location_id = fields.Many2one(
        'hr.work.location',
        string='Địa điểm',
        help='Địa điểm được chọn từ dropdown'
    )
    
    # Processing info
    processed = fields.Boolean(
        string='Đã xử lý',
        default=False,
        index=True
    )
    
    process_note = fields.Text(
        string='Ghi chú xử lý'
    )
    
    attendance_id = fields.Many2one(
        'hr.attendance',
        string='Bản ghi chấm công',
        help='Bản ghi hr.attendance được tạo từ log này'
    )
    
    # Approval workflow
    approver_id = fields.Many2one(
        'res.users',
        string='Người duyệt'
    )
    
    approval_note = fields.Text(
        string='Ghi chú duyệt'
    )
    
    approval_date = fields.Datetime(
        string='Ngày duyệt'
    )
    
    # Retry counter
    retry_count = fields.Integer(
        string='Số lần thử lại',
        default=0
    )
    
    error_message = fields.Text(
        string='Thông báo lỗi'
    )
    
    _sql_constraints = [
        ('uniq_emp_time_action',
         'UNIQUE(employee_id, timestamp, action)',
         'Duplicate attendance log detected!'),
    ]
    
    @api.model
    def create(self, vals):
        """Validate trước khi tạo log"""
        if 'timestamp' not in vals or not vals.get('timestamp'):
            vals['timestamp'] = fields.Datetime.now()
        
        # Check duplicate trong 3 giây
        try:
            existing = self.search([
                ('employee_id', '=', vals.get('employee_id')),
                ('action', '=', vals.get('action')),
                ('processed', '=', False),
                ('timestamp', '>=', fields.Datetime.to_string(
                    fields.Datetime.from_string(vals['timestamp']) - timedelta(seconds=3)
                )),
                ('timestamp', '<=', fields.Datetime.to_string(
                    fields.Datetime.from_string(vals['timestamp']) + timedelta(seconds=3)
                ))
            ], limit=1)
            
            if existing:
                _logger.warning(
                    'Preventing near-duplicate attendance log for employee %s at %s',
                    vals.get('employee_id'), vals.get('timestamp')
                )
                raise ValidationError(_('Bạn vừa mới chấm công rồi! Vui lòng chờ ít nhất 3 giây.'))
        except Exception as e:
            if isinstance(e, ValidationError):
                raise
            _logger.error(f'Error checking duplicate: {e}')
        
        return super().create(vals)
    
    def action_process(self):
        """Xử lý log thành bản ghi chấm công thực"""
        for record in self:
            if record.processed:
                continue
            
            try:
                record.state = 'processing'
                
                # Prepare attendance values
                vals = {
                    'employee_id': record.employee_id.id,
                }
                
                # Add GPS data
                if record.latitude and record.longitude:
                    if record.action == 'check_in':
                        vals.update({
                            'check_in_latitude': record.latitude,
                            'check_in_longitude': record.longitude,
                        })
                    else:
                        vals.update({
                            'check_out_latitude': record.latitude,
                            'check_out_longitude': record.longitude,
                        })
                
                # Add work location
                if record.work_location_id:
                    vals['work_location_id'] = record.work_location_id.id
                
                # Create or update attendance
                if record.action == 'check_in':
                    vals['check_in'] = record.timestamp
                    attendance = self.env['hr.attendance'].sudo().create(vals)
                else:
                    # Find last check-in without check-out
                    last_attendance = self.env['hr.attendance'].sudo().search([
                        ('employee_id', '=', record.employee_id.id),
                        ('check_out', '=', False)
                    ], limit=1, order='check_in desc')
                    
                    if not last_attendance:
                        raise ValidationError(_('Không tìm thấy bản ghi check-in để check-out!'))
                    
                    last_attendance.write({
                        'check_out': record.timestamp,
                        'check_out_latitude': record.latitude,
                        'check_out_longitude': record.longitude,
                    })
                    attendance = last_attendance
                
                # Mark as processed
                record.write({
                    'processed': True,
                    'state': 'processed',
                    'attendance_id': attendance.id,
                    'process_note': _('Đã xử lý thành công')
                })
                
                _logger.info(f'Processed attendance log {record.id} -> attendance {attendance.id}')
                
            except Exception as e:
                _logger.error(f'Error processing log {record.id}: {e}')
                record.write({
                    'state': 'failed',
                    'error_message': str(e),
                    'retry_count': record.retry_count + 1
                })
    
    def action_approve(self):
        """Duyệt log (workflow)"""
        for record in self:
            record.write({
                'state': 'processed',
                'approver_id': self.env.uid,
                'approval_date': fields.Datetime.now(),
            })
            if not record.processed:
                record.action_process()
    
    def action_reject(self):
        """Từ chối log"""
        for record in self:
            record.write({
                'state': 'rejected',
                'approver_id': self.env.uid,
                'approval_date': fields.Datetime.now(),
                'processed': True,
            })
    
    @api.model
    def cron_process_pending_logs(self):
        """
        Cron job xử lý các log đang chờ
        Chạy mỗi 1 phút
        """
        pending_logs = self.search([
            ('state', '=', 'pending'),
            ('processed', '=', False),
        ], limit=100)
        
        _logger.info(f'Processing {len(pending_logs)} pending attendance logs...')
        
        for log in pending_logs:
            try:
                log.action_process()
            except Exception as e:
                _logger.error(f'Failed to process log {log.id}: {e}')
        
        return True
    
    @api.model
    def cron_retry_failed_logs(self):
        """
        Cron job thử lại các log thất bại
        Chạy mỗi 5 phút, retry tối đa 3 lần
        """
        failed_logs = self.search([
            ('state', '=', 'failed'),
            ('retry_count', '<', 3),
        ], limit=50)
        
        _logger.info(f'Retrying {len(failed_logs)} failed attendance logs...')
        
        for log in failed_logs:
            try:
                log.write({'state': 'pending'})
                log.action_process()
            except Exception as e:
                _logger.error(f'Retry failed for log {log.id}: {e}')
        
        return True
