# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HrAttendanceExplanation(models.Model):
    _name = 'hr.attendance.explanation'
    _description = 'Attendance Explanation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'
    
    name = fields.Char(string='Số tham chiếu', required=True, copy=False, readonly=True, 
                       default=lambda self: _('New'))
    employee_id = fields.Many2one('hr.employee', string='Nhân viên', required=True, 
                                   default=lambda self: self.env.user.employee_id)
    date = fields.Date(string='Ngày', required=True, default=fields.Date.today)
    submission_type_id = fields.Many2one('submission.type', string='Loại giải trình', required=True)
    attendance_id = fields.Many2one('hr.attendance', string='Bản ghi chấm công')
    
    # Time fields
    expected_check_in = fields.Datetime(string='Giờ vào dự kiến')
    expected_check_out = fields.Datetime(string='Giờ ra dự kiến')
    actual_check_in = fields.Datetime(string='Giờ vào thực tế')
    actual_check_out = fields.Datetime(string='Giờ ra thực tế')
    
    # Explanation
    reason = fields.Text(string='Lý do', required=True)
    attachment_ids = fields.Many2many('ir.attachment', string='Tài liệu đính kèm')
    
    # Approval
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('submitted', 'Đã gửi'),
        ('approved', 'Đã duyệt'),
        ('refused', 'Từ chối'),
    ], string='Trạng thái', default='draft', tracking=True)
    
    approver_id = fields.Many2one('res.users', string='Người phê duyệt')
    approval_date = fields.Datetime(string='Ngày phê duyệt')
    refusal_reason = fields.Text(string='Lý do từ chối')
    
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('hr.attendance.explanation') or _('New')
        return super().create(vals)
    
    def action_submit(self):
        """Submit explanation for approval"""
        self.ensure_one()
        self.write({
            'state': 'submitted',
        })
        # TODO: Send notification to manager
        
    def action_approve(self):
        """Approve explanation"""
        self.ensure_one()
        if not self.env.user.has_group('hr_attendance.group_hr_attendance_manager'):
            raise ValidationError(_('Chỉ quản lý chấm công mới có thể phê duyệt.'))
            
        self.write({
            'state': 'approved',
            'approver_id': self.env.user.id,
            'approval_date': fields.Datetime.now(),
        })
        
        # Link to attendance record if exists
        if self.attendance_id:
            self.attendance_id.explanation_id = self.id
    
    def action_refuse(self):
        """Open wizard to refuse explanation"""
        self.ensure_one()
        return {
            'name': _('Từ chối giải trình'),
            'type': 'ir.actions.act_window',
            'res_model': 'reason.for.refuse.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_explanation_id': self.id,
            },
        }
    
    def action_reset_to_draft(self):
        """Reset to draft"""
        self.ensure_one()
        self.write({
            'state': 'draft',
        })
