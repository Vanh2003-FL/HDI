# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class HrAttendanceLog(models.Model):
    """Async Attendance Log Queue - Prevent double click, batch processing"""
    _name = 'hr.attendance.log'
    _description = 'Attendance Log - Async Processing Queue'
    _order = 'create_date desc'
    
    # === CORE FIELDS ===
    employee_id = fields.Many2one(
        'hr.employee',
        string='Nhân viên',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    action = fields.Selection([
        ('check_in', 'Check In'),
        ('check_out', 'Check Out'),
    ], string='Hành động', required=True)
    
    timestamp = fields.Datetime(
        string='Thời gian',
        required=True,
        default=fields.Datetime.now,
        index=True
    )
    
    state = fields.Selection([
        ('pending', 'Chờ xử lý'),
        ('processing', 'Đang xử lý'),
        ('processed', 'Đã xử lý'),
        ('rejected', 'Bị từ chối'),
        ('failed', 'Thất bại'),
    ], string='Trạng thái', default='pending', required=True, index=True)
    
    # === PROCESSING INFO ===
    attendance_id = fields.Many2one(
        'hr.attendance',
        string='Attendance Record',
        ondelete='set null'
    )
    
    processed = fields.Boolean(
        string="Đã xử lý",
        default=False,
        index=True
    )
    
    process_note = fields.Text(string='Ghi chú xử lý')
    
    # === APPROVAL (Optional) ===
    approver_id = fields.Many2one('res.users', string='Người duyệt')
    approval_note = fields.Text(string='Ghi chú duyệt')
    approval_date = fields.Datetime(string='Ngày duyệt')
    
    # === METADATA ===
    create_date = fields.Datetime(string='Ngày tạo', readonly=True)
    
    # === CONSTRAINTS ===
    _sql_constraints = [
        ('uniq_emp_time_action',
         'UNIQUE(employee_id, timestamp, action)',
         'Duplicate attendance log for same employee, time and action.'),
    ]
    
    # === CRUD OVERRIDES ===
    @api.model_create_multi
    def create(self, vals_list):
        """Prevent near-duplicate entries - batch support for Odoo 18"""
        for vals in vals_list:
            if 'timestamp' not in vals or not vals.get('timestamp'):
                vals['timestamp'] = fields.Datetime.now()
            
            # Check for near-duplicates (within 3 seconds)
            try:
                timestamp_dt = fields.Datetime.from_string(vals['timestamp'])
                check_time = timestamp_dt - timedelta(seconds=3)
                
                existing = self.search([
                    ('employee_id', '=', vals.get('employee_id')),
                    ('action', '=', vals.get('action')),
                    ('processed', '=', False),
                    ('timestamp', '>=', fields.Datetime.to_string(check_time))
                ], limit=1)
                
                if existing:
                    _logger.warning(
                        'Preventing near-duplicate attendance log for employee %s',
                        vals.get('employee_id')
                    )
                    raise ValidationError(_(
                        'Yêu cầu chấm công gần giống nhau đã được phát hiện. '
                        'Vui lòng đợi vài giây trước khi thử lại.'
                    ))
            except Exception as e:
                if isinstance(e, ValidationError):
                    raise
                _logger.error('Error checking duplicates: %s', e)
        
        return super().create(vals_list)
    
    # === PROCESSING METHODS ===
    def mark_processed(self, note=None):
        """Mark log as processed"""
        for rec in self:
            rec.processed = True
            rec.state = 'processed'
            if note:
                rec.process_note = (rec.process_note or '') + '\n' + note
    
    def action_approve(self):
        """Approve log"""
        for rec in self:
            rec.state = 'processed'
            rec.approver_id = self.env.uid
            rec.approval_date = fields.Datetime.now()
    
    def action_reject(self, note=None):
        """Reject log"""
        for rec in self:
            rec.state = 'rejected'
            rec.approver_id = self.env.uid
            rec.approval_date = fields.Datetime.now()
            if note:
                rec.approval_note = note
    
    # === CRON JOB ===
    @api.model
    def process_pending_batch(self, batch_size=50):
        """Process pending logs in batch"""
        pending = self.search(
            [('state', '=', 'pending')],
            limit=batch_size,
            order='create_date asc'
        )
        
        if not pending:
            return 0
        
        processed_count = 0
        for rec in pending:
            try:
                rec.state = 'processing'
                
                if not rec.employee_id:
                    rec.process_note = 'Missing employee'
                    rec.state = 'rejected'
                    continue
                
                # Simple processing - just mark as done
                # Real attendance is created by _attendance_action_change
                rec.process_note = f"Attendance {rec.action} at {rec.timestamp} recorded"
                rec.mark_processed()
                processed_count += 1
                
            except Exception as e:
                _logger.exception('Failed to process attendance log %s: %s', rec.id, e)
                rec.process_note = 'Processing error: %s' % str(e)
                rec.state = 'failed'
        
        _logger.info('Processed %d attendance logs', processed_count)
        return processed_count
    
    @api.model
    def cron_process_pending_logs(self):
        """Cron job entry point"""
        return self.process_pending_batch()
    
    @api.model
    def clean_old_logs(self, days=90):
        """Clean old processed logs"""
        cutoff_date = fields.Datetime.now() - timedelta(days=days)
        old_logs = self.search([
            ('state', '=', 'processed'),
            ('create_date', '<', cutoff_date)
        ])
        
        count = len(old_logs)
        old_logs.unlink()
        
        _logger.info('Cleaned %d old attendance logs', count)
        return count
    
    # === REPORTING ===
    def name_get(self):
        """Custom name_get"""
        result = []
        for rec in self:
            name = f"{rec.employee_id.name} - {rec.action} - {rec.timestamp.strftime('%d/%m/%Y %H:%M')}"
            result.append((rec.id, name))
        return result
