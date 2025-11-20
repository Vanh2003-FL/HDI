# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class ReasonForRefuseWizard(models.TransientModel):
    """Wizard để nhập lý do từ chối giải trình"""
    _name = 'reason.for.refuse.wizard'
    _description = 'Wizard to refuse attendance explanation'
    
    hr_attendance_explanation_id = fields.Many2one(
        'hr.attendance.explanation',
        string='Giải trình chấm công',
        required=True,
        ondelete='cascade'
    )
    
    reason_for_refuse = fields.Text(
        string='Lý do từ chối',
        required=True,
        placeholder='Nhập lý do từ chối chi tiết...'
    )
    
    def action_refuse(self):
        """Thực hiện từ chối với lý do"""
        self.ensure_one()
        
        explanation = self.hr_attendance_explanation_id.sudo()
        
        # Check permissions
        if not explanation.condition_visible_button_refuse_approve:
            raise UserError(_('Bạn không được phép từ chối bản ghi này'))
        
        # Update current approver
        approver = explanation.approver_ids.filtered(
            lambda a: a.user_id == self.env.user
        )
        
        if approver:
            approver.write({
                'status': 'refused',
                'approval_note': self.reason_for_refuse,
                'approval_date': fields.Datetime.now(),
            })
        
        # Update explanation state
        explanation.write({
            'state': 'refuse',
            'reason_for_refuse': self.reason_for_refuse,
        })
        
        # Send notification to employee
        explanation._send_notify(
            f'Bản ghi Giải trình của bạn đã bị từ chối. Lý do: {self.reason_for_refuse}',
            explanation.employee_id.user_id
        )
        
        return {'type': 'ir.actions.act_window_close'}
    refusal_reason = fields.Text(string='Lý do từ chối', required=True)
    
    def action_refuse(self):
        """Refuse the explanation with reason"""
        self.ensure_one()
        
        if not self.env.user.has_group('hdi_attendance.group_attendance_manager'):
            raise ValidationError(_('Chỉ quản lý chấm công mới có thể từ chối giải trình.'))
        
        self.explanation_id.write({
            'state': 'refused',
            'approver_id': self.env.user.id,
            'approval_date': fields.Datetime.now(),
            'refusal_reason': self.refusal_reason,
        })
        
        return {'type': 'ir.actions.act_window_close'}
