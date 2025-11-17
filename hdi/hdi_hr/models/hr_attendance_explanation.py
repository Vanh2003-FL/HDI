# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrAttendanceExplanation(models.Model):
    """Model lưu giải trình chấm công"""
    _name = 'hr.attendance.explanation'
    _description = 'Giải trình chấm công'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    
    attendance_id = fields.Many2one(
        'hr.attendance',
        string='Bản ghi chấm công',
        required=True,
        ondelete='cascade'
    )
    
    employee_id = fields.Many2one(
        'hr.employee',
        string='Nhân viên',
        required=True,
        readonly=True
    )
    
    explanation_date = fields.Date(
        string='Ngày giải trình',
        required=True
    )
    
    hdi_reason = fields.Text(
        string='Lý do',
        required=True,
        tracking=True
    )
    
    hdi_explanation_state = fields.Selection([
        ('draft', 'Nháp'),
        ('submitted', 'Đã gửi'),
        ('approved', 'Đã duyệt'),
        ('rejected', 'Từ chối'),
    ], string='Trạng thái', default='draft', required=True, tracking=True)
    
    hdi_reviewer_id = fields.Many2one(
        'res.users',
        string='Người duyệt',
        tracking=True
    )
    
    hdi_review_date = fields.Datetime(
        string='Ngày duyệt',
        tracking=True
    )
    
    hdi_review_note = fields.Text(
        string='Ghi chú duyệt',
        tracking=True
    )
    
    def action_submit(self):
        """Gửi giải trình"""
        for rec in self:
            rec.hdi_explanation_state = 'submitted'
            # TODO: Send notification to manager
    
    def action_approve(self):
        """Duyệt giải trình"""
        for rec in self:
            rec.write({
                'hdi_explanation_state': 'approved',
                'hdi_reviewer_id': self.env.user.id,
                'hdi_review_date': fields.Datetime.now(),
            })
    
    def action_reject(self):
        """Từ chối giải trình"""
        for rec in self:
            rec.write({
                'hdi_explanation_state': 'rejected',
                'hdi_reviewer_id': self.env.user.id,
                'hdi_review_date': fields.Datetime.now(),
            })
