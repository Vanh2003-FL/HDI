# -*- coding: utf-8 -*-
from odoo import models, api


class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    
    def get_working_locations(self):
        """Get list of work locations for attendance check-in"""
        self.ensure_one()
        
        WorkLocation = self.env['hr.work.location'].sudo()
        locations = WorkLocation.search([('active', '=', True)])
        
        result = []
        default_location = self.work_location_id.id if self.work_location_id else False
        
        for location in locations:
            result.append({
                'id': location.id,
                'name': location.name,
                'default_value': default_location,
            })
        
        return result
    
    def get_en_checked_diff_ok(self):
        """Check if employee can check in at different location"""
        self.ensure_one()
        # Logic: Allow check in at different location if already checked in
        return self.attendance_state == 'checked_in'
