# -*- coding: utf-8 -*-
import logging
from datetime import timedelta

from odoo.exceptions import ValidationError

from odoo import models, fields, api, _, exceptions

_logger = logging.getLogger(__name__)


class HrAttendanceLog(models.Model):
    _name = 'hr.attendance.log'
    _description = 'Async Attendance Log (queue)'
    _order = 'create_date desc'

    employee_id = fields.Many2one(
        'hr.employee', string='Nhân viên', required=True, ondelete='cascade')
    action = fields.Selection(
        [
            ('check_in', 'Check In'),
            ('check_out', 'Check Out')
        ],
        string="Hành động",
        required=True
    )
    timestamp = fields.Datetime(
        string='Thời gian', required=True, default=fields.Datetime.now)
    state = fields.Selection(
        [
            ('pending', 'Chờ xử lý'),
            ('processing', 'Đang xử lý'),
            ('processed', 'Đã xử lý'),
            ('rejected', 'Bị từ chối'),
            ('failed', 'Thất bại'),
        ],
        string="Trạng thái",
        default='pending',
        required=True,
    )
    processed = fields.Boolean(string="Đã xử lý", default=False)
    process_note = fields.Text(string='Ghi chú xử lý')
    approver_id = fields.Many2one('res.users', string='Người duyệt')
    approval_note = fields.Text(string='Ghi chú duyệt')
    approval_date = fields.Datetime(string='Ngày duyệt')
    create_date = fields.Datetime(string='Ngày tạo', readonly=True)

    _sql_constraints = [
        ('uniq_emp_time_action', 'UNIQUE(employee_id, timestamp, action)',
         'Duplicate attendance log for same employee, time and action.'),
    ]

    @api.model
    def create(self, vals):
        if 'timestamp' not in vals or not vals.get('timestamp'):
            vals['timestamp'] = fields.Datetime.now()

        try:
            existing = self.search([
                ('employee_id', '=', vals.get('employee_id')),
                ('action', '=', vals.get('action')),
                ('processed', '=', False),
                ('timestamp', '>=', fields.Datetime.to_string(
                    fields.Datetime.from_string(vals['timestamp']) - timedelta(seconds=3)
                ))
            ], limit=1)
            if existing:
                _logger.warning(
                    'Preventing near-duplicate attendance log for employee %s',
                    vals.get('employee_id')
                )
                raise ValidationError(_('Duplicate or near-duplicate attendance request detected.'))
        except Exception:
            pass

        return super().create(vals)

    def mark_processed(self, note=None):
        for rec in self:
            rec.processed = True
            rec.state = 'processed'
            if note:
                rec.process_note = (rec.process_note or '') + '\n' + note

    def action_approve(self):
        for rec in self:
            rec.state = 'processed'
            rec.approver_id = self.env.uid
            rec.approval_date = fields.Datetime.now()

    def action_reject(self, note=None):
        for rec in self:
            rec.state = 'rejected'
            rec.approver_id = self.env.uid
            rec.approval_date = fields.Datetime.now()
            if note:
                rec.approval_note = note

    # Cron xử lý bất đồng bộ
    @api.model
    def process_pending_batch(self, batch_size=50):
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
                rec.process_note = f"Attendance {rec.action} at {rec.timestamp} recorded"
                rec.mark_processed()
                processed_count += 1

            except Exception as e:
                _logger.exception('Failed to process attendance log %s: %s', rec.id, e)
                rec.process_note = 'Processing error: %s' % e
                rec.state = 'failed'

        return processed_count

    @api.model
    def cron_cleanup_old_logs(self, age_days=365, batch_size=200):
        cutoff = fields.Datetime.now() - timedelta(days=age_days)
        old = self.search([('create_date', '<', cutoff)], limit=batch_size)
        if not old:
            return 0
        count = len(old)
        old.unlink()
        _logger.info('Cleaned up %s old attendance logs', count)
        return count
