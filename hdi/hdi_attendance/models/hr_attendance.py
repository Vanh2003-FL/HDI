# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    # Additional fields
    work_location_id = fields.Many2one('hr.work.location', string='Địa điểm làm việc')
    note = fields.Text(string='Ghi chú')
    explanation_required = fields.Boolean(string='Cần giải trình', compute='_compute_explanation_required', store=True)
    explanation_id = fields.Many2one('hr.attendance.explanation', string='Giải trình', readonly=True)
    
    @api.depends('check_in', 'check_out', 'employee_id')
    def _compute_explanation_required(self):
        """Check if attendance requires explanation"""
        for attendance in self:
            # Logic: Cần giải trình nếu thiếu check in/out hoặc các trường hợp bất thường
            attendance.explanation_required = False
            
    def button_create_explanation(self):
        """Open wizard to create attendance explanation"""
        self.ensure_one()
        return {
            'name': _('Giải trình chấm công'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.attendance.explanation',
            'view_mode': 'form',
            'context': {
                'default_attendance_id': self.id,
                'default_employee_id': self.employee_id.id,
                'default_date': self.check_in.date() if self.check_in else fields.Date.today(),
            },
            'target': 'new',
        }
        
    @api.model
    def _attendance_action_change(self):
        """Override to add async logging - prevent double click"""
        result = super()._attendance_action_change()
        
        # Log the action
        if result:
            self.env['hr.attendance.log'].create({
                'attendance_id': result.get('attendance', {}).get('id'),
                'employee_id': self.env.user.employee_id.id,
                'action_time': fields.Datetime.now(),
                'action_type': result.get('action'),
            })
            
        return result
