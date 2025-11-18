# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class HrEmployee(models.Model):
    """
    Extend hr.employee để support chấm công
    """
    _inherit = 'hr.employee'
    
    # Default work location
    default_work_location_id = fields.Many2one(
        'hr.work.location',
        string='Địa điểm mặc định',
        help='Địa điểm làm việc mặc định khi chấm công'
    )
    
    # Allow different location for check-out
    allow_different_checkout_location = fields.Boolean(
        string='Cho phép checkout khác địa điểm',
        default=True,
        help='Cho phép checkout ở địa điểm khác với check-in'
    )
    
    @api.model
    def get_available_work_locations(self):
        """
        Lấy danh sách địa điểm làm việc cho dropdown
        Called from JavaScript
        """
        locations = self.env['hr.work.location'].search([
            ('active', '=', True)
        ], order='is_default desc, name')
        
        result = []
        default_id = False
        
        for loc in locations:
            result.append({
                'id': loc.id,
                'name': loc.name,
                'address': loc.address or '',
                'is_default': loc.is_default,
            })
            if loc.is_default:
                default_id = loc.id
        
        # If employee has default location, prioritize it
        employee = self.env.user.employee_id
        if employee and employee.default_work_location_id:
            default_id = employee.default_work_location_id.id
        
        return {
            'locations': result,
            'default_id': default_id,
        }
    
    @api.model
    def check_allow_different_location(self):
        """
        Kiểm tra xem nhân viên có được phép checkout khác địa điểm không
        Called from JavaScript
        """
        employee = self.env.user.employee_id
        return employee.allow_different_checkout_location if employee else True
