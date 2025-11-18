# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AttendanceCheckinWizard(models.TransientModel):
    """
    Wizard cho chấm công manual (nếu cần)
    """
    _name = 'attendance.checkin.wizard'
    _description = 'Attendance Check-in Wizard'
    
    employee_id = fields.Many2one(
        'hr.employee',
        string='Nhân viên',
        required=True,
        default=lambda self: self.env.user.employee_id
    )
    
    work_location_id = fields.Many2one(
        'hr.work.location',
        string='Địa điểm',
        required=True
    )
    
    latitude = fields.Float(
        string='Vĩ độ',
        digits=(10, 7)
    )
    
    longitude = fields.Float(
        string='Kinh độ',
        digits=(10, 7)
    )
    
    def action_check_in(self):
        """Manual check-in"""
        self.ensure_one()
        
        vals = {
            'employee_id': self.employee_id.id,
            'check_in': fields.Datetime.now(),
            'work_location_id': self.work_location_id.id,
        }
        
        if self.latitude and self.longitude:
            vals.update({
                'check_in_latitude': self.latitude,
                'check_in_longitude': self.longitude,
            })
        
        attendance = self.env['hr.attendance'].create(vals)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Check-in thành công!'),
                'message': _('Bạn đã check-in lúc %s') % attendance.check_in,
                'type': 'success',
                'sticky': False,
            }
        }
