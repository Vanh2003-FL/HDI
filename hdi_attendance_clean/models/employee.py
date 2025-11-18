# -*- coding: utf-8 -*-
from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    attendance_count = fields.Integer(string='Attendance Count', compute='_compute_attendance_count')
    default_work_location_id = fields.Many2one('hdi.work.location', string='Default Work Location')
    
    def _compute_attendance_count(self):
        for employee in self:
            employee.attendance_count = self.env['hr.attendance'].search_count([
                ('employee_id', '=', employee.id)
            ])
    
    def action_view_attendances(self):
        self.ensure_one()
        return {
            'name': 'Attendances',
            'type': 'ir.actions.act_window',
            'res_model': 'hr.attendance',
            'view_mode': 'tree,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id}
        }

    def get_working_locations(self):
        """Get list of working locations for employee"""
        self.ensure_one()
        locations = self.env['hdi.work.location'].search([
            ('active', '=', True),
            '|', ('company_id', '=', False), ('company_id', '=', self.company_id.id)
        ])
        
        result = []
        default_location = self.env['hdi.work.location'].search([], limit=1)
        
        for loc in locations:
            result.append({
                'id': loc.id,
                'name': loc.name,
                'default_value': default_location.id if default_location else False,
            })
        
        return result

    def get_en_checked_diff_ok(self):
        """Check if user can checkout at different location"""
        self.ensure_one()
        return True

    def attendance_manual(self, next_action, entered_pin=None):
        """Override to add GPS tracking and location"""
        latitude = self._context.get('latitude', False)
        longitude = self._context.get('longitude', False)
        hdi_location_id = self._context.get('hdi_location_id', False)
        
        _logger.info('HDI attendance_manual: %s - %s - lat: %s, lon: %s, location: %s', 
                     self.name, self.id, latitude, longitude, hdi_location_id)
        
        # Call parent method which will create/update attendance record
        # Our hr.attendance override will capture the GPS coordinates from context
        result = super(HrEmployee, self).attendance_manual(next_action, entered_pin)
        
        # Update the attendance record with location if provided
        if hdi_location_id:
            attendance = self.env['hr.attendance'].search([
                ('employee_id', '=', self.id),
                ('check_out', '=', False)
            ], limit=1, order='check_in desc')
            
            if attendance:
                attendance.write({'work_location_id': hdi_location_id})
        
        return result
