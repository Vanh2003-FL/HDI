# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    attendance_count = fields.Integer(string='Attendance Count', compute='_compute_attendance_count')
    default_work_location_id = fields.Many2one('hdi.work.location', string='Default Work Location')
    
    def _compute_attendance_count(self):
        for employee in self:
            employee.attendance_count = self.env['hdi.attendance'].search_count([
                ('employee_id', '=', employee.id)
            ])
    
    def action_view_attendances(self):
        self.ensure_one()
        return {
            'name': 'Attendances',
            'type': 'ir.actions.act_window',
            'res_model': 'hdi.attendance',
            'view_mode': 'tree,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id}
        }
