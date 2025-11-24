# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ReasonForRefuseWizard(models.TransientModel):
    _name = 'reason.for.refuse.wizard'
    _description = 'Reason for refusing attendance explanation'
    
    explanation_id = fields.Many2one(
        'hr.attendance.explanation',
        string='Giải trình chấm công',
        required=True
    )
    reason = fields.Text(string='Lý do từ chối', required=True)
    
    def action_confirm(self):
        """Confirm refusal with reason"""
        self.ensure_one()
        
        # Update explanation state
        self.explanation_id.write({
            'state': 'refuse',
            'refusal_reason': self.reason,
        })
        
        # Update approver status
        approver = self.explanation_id.approver_ids.filtered(
            lambda a: a.user_id == self.env.user and a.state == 'pending'
        )
        if approver:
            approver.write({
                'state': 'refuse',
                'approval_date': fields.Datetime.now(),
                'comment': self.reason
            })
        
        # Send notification to employee
        if self.explanation_id.employee_id.user_id:
            self.explanation_id.message_post(
                body=_('Giải trình chấm công của bạn đã bị từ chối.<br/>Lý do: %s') % self.reason,
                partner_ids=[self.explanation_id.employee_id.user_id.partner_id.id],
                message_type='notification'
            )
        
        return {'type': 'ir.actions.act_window_close'}
