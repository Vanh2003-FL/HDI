# -*- coding: utf-8 -*-
from odoo import fields, models, api, _


class ApprovalApprover(models.Model):
    """Model quản lý người phê duyệt trong quy trình"""
    _name = 'approval.approver'
    _description = 'Approval Approver'
    _order = 'sequence, id'
    
    # Link to explanation
    hr_attendance_explanation_id = fields.Many2one(
        'hr.attendance.explanation',
        string="Giải trình chấm công",
        ondelete='cascade',
        index=True
    )
    
    # Approver info
    user_id = fields.Many2one(
        'res.users',
        string='Người phê duyệt',
        required=True,
        ondelete='cascade'
    )
    
    status = fields.Selection([
        ('new', 'Mới'),
        ('pending', 'Chờ duyệt'),
        ('approved', 'Đã duyệt'),
        ('refused', 'Từ chối'),
    ], string='Trạng thái', default='new', required=True)
    
    sequence = fields.Integer(
        string="Thứ tự phê duyệt",
        default=1,
        help="Thứ tự trong quy trình phê duyệt (người có sequence nhỏ hơn phê duyệt trước)"
    )
    
    role_selection = fields.Char(
        string='Vai trò',
        help='Vai trò trong quy trình (VD: Manager, Block Lead, Department Head)'
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Công ty',
        default=lambda self: self.env.company
    )
    
    # Approval details
    approval_date = fields.Datetime(string='Ngày phê duyệt', readonly=True)
    approval_note = fields.Text(string='Ghi chú phê duyệt')
    
    def action_approve(self):
        """Approve request"""
        self.ensure_one()
        self.write({
            'status': 'approved',
            'approval_date': fields.Datetime.now(),
        })
        
        # Trigger parent explanation approval logic
        if self.hr_attendance_explanation_id:
            self.hr_attendance_explanation_id.button_approve()
    
    def action_refuse(self):
        """Refuse request"""
        self.ensure_one()
        self.write({
            'status': 'refused',
            'approval_date': fields.Datetime.now(),
        })
        
        # Update explanation state
        if self.hr_attendance_explanation_id:
            self.hr_attendance_explanation_id.write({
                'state': 'refuse',
                'reason_for_refuse': self.approval_note or _('Từ chối bởi %s') % self.user_id.name,
            })
