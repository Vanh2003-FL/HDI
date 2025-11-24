# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class HrWorkLocation(models.Model):
    _inherit = 'hr.work.location'
    
    code = fields.Char(
        string='Mã',
        required=False,
        help='Mã định danh duy nhất cho địa điểm'
    )
    
    sequence = fields.Integer(
        string='Thứ tự',
        default=10
    )
    
    location_type = fields.Selection([
        ('office', 'Văn phòng'),
        ('home', 'Làm từ xa'),
        ('other', 'Khác'),
    ], string='Loại địa điểm', default='office')
    
    # GPS Information
    latitude = fields.Float(
        string='Vĩ độ',
        digits=(10, 7),
        help='Vĩ độ GPS của văn phòng'
    )
    
    longitude = fields.Float(
        string='Kinh độ',
        digits=(10, 7),
        help='Kinh độ GPS của văn phòng'
    )
    
    # Address
    address = fields.Text(
        string='Địa chỉ',
        help='Địa chỉ đầy đủ của văn phòng'
    )
    
    # Location validation settings
    max_distance_allowed = fields.Float(
        string='Khoảng cách tối đa cho phép (km)',
        default=0.5,
        help='Khoảng cách tối đa từ vị trí chấm công đến văn phòng (đơn vị: km)'
    )
    
    allow_overtime_attendance = fields.Boolean(
        string='Cho phép chấm công ngoài giờ',
        default=True
    )
    
    # Display
    location_url = fields.Char(
        string='Link Google Maps',
        compute='_compute_location_url',
        help='Link xem vị trí trên Google Maps'
    )
    
    note = fields.Text(
        string='Ghi chú'
    )

    @api.depends('latitude', 'longitude')
    def _compute_location_url(self):
        """Tạo link Google Maps"""
        for location in self:
            if location.latitude and location.longitude:
                location.location_url = "https://www.google.com/maps?q=%s,%s" % (
                    location.latitude,
                    location.longitude
                )
            else:
                location.location_url = ''

    def action_view_employees(self):
        """Xem danh sách nhân viên thuộc địa điểm"""
        self.ensure_one()
        return {
            'name': _('Nhân viên - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee',
            'view_mode': 'tree,form',
            'domain': [('work_location_id', '=', self.id)],
            'context': {'default_work_location_id': self.id}
        }

    def action_view_attendances(self):
        """Xem lịch sử chấm công tại địa điểm"""
        self.ensure_one()
        employee_ids = self.env['hr.employee'].search([
            ('work_location_id', '=', self.id)
        ]).ids
        
        return {
            'name': _('Chấm công - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'hr.attendance',
            'view_mode': 'tree,form',
            'domain': [('employee_id', 'in', employee_ids)],
            'context': {'search_default_today': 1}
        }

    def action_view_on_map(self):
        """Mở vị trí trên Google Maps"""
        self.ensure_one()
        if self.location_url:
            return {
                'type': 'ir.actions.act_url',
                'url': self.location_url,
                'target': 'new',
            }
        raise UserError(_('Vui lòng cập nhật tọa độ GPS cho địa điểm!'))
