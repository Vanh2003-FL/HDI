# -*- coding: utf-8 -*-

from odoo import fields, models, _


class HrEmployeeOnboardingWizard(models.TransientModel):
    _name = 'hr.employee.onboarding.wizard'
    _description = 'Wizard hướng dẫn nhân viên mới'

    employee_id = fields.Many2one('hr.employee', string='Nhân viên', required=True)
    
    # Checklist items
    profile_completed = fields.Boolean(string='Hoàn thành hồ sơ')
    contract_signed = fields.Boolean(string='Ký hợp đồng lao động')
    equipment_received = fields.Boolean(string='Nhận trang thiết bị')
    account_created = fields.Boolean(string='Tạo tài khoản hệ thống')
    orientation_attended = fields.Boolean(string='Tham gia định hướng')
    
    notes = fields.Text(string='Ghi chú')

    def action_complete(self):
        """Hoàn thành onboarding"""
        self.ensure_one()
        progress = 0
        if self.profile_completed: progress += 20
        if self.contract_signed: progress += 20
        if self.equipment_received: progress += 20
        if self.account_created: progress += 20
        if self.orientation_attended: progress += 20
        
        self.employee_id.write({
            'hdi_onboarding_progress': progress,
            'hdi_is_onboarding': progress < 100,
        })
        
        return {'type': 'ir.actions.act_window_close'}
