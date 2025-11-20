# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ReasonForRefuseWizard(models.TransientModel):
    _name = 'reason.for.refuse.wizard'
    _description = 'Wizard to refuse attendance explanation'
    
    explanation_id = fields.Many2one('hr.attendance.explanation', string='Giải trình', required=True)
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
