# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrWorkLocation(models.Model):
    """
    Model quản lý địa điểm làm việc
    Kế thừa từ Odoo 18 core hr.work.location
    """
    _inherit = 'hr.work.location'
    
    # GPS Coordinates
    latitude = fields.Float(
        string='Vĩ độ',
        digits=(10, 7),
        help='Vĩ độ GPS của địa điểm'
    )
    
    longitude = fields.Float(
        string='Kinh độ',
        digits=(10, 7),
        help='Kinh độ GPS của địa điểm'
    )
    
    # Radius for attendance validation
    radius = fields.Float(
        string='Bán kính cho phép (m)',
        default=500,
        help='Bán kính tính từ tọa độ trung tâm (đơn vị: mét). '
             'Chấm công ngoài bán kính này sẽ bị cảnh báo.'
    )
    
    # Address
    address = fields.Char(
        string='Địa chỉ',
        help='Địa chỉ chi tiết của địa điểm'
    )
    
    # Default location
    is_default = fields.Boolean(
        string='Địa điểm mặc định',
        default=False,
        help='Đánh dấu là địa điểm mặc định khi chấm công'
    )
    
    # Active
    active = fields.Boolean(
        default=True
    )
    
    # Computed fields
    coordinates_display = fields.Char(
        string='Tọa độ',
        compute='_compute_coordinates_display',
        store=False
    )
    
    google_maps_url = fields.Char(
        string='Google Maps',
        compute='_compute_google_maps_url',
        store=False
    )
    
    @api.depends('latitude', 'longitude')
    def _compute_coordinates_display(self):
        """Hiển thị tọa độ dạng text"""
        for record in self:
            if record.latitude and record.longitude:
                record.coordinates_display = f'{record.latitude:.6f}, {record.longitude:.6f}'
            else:
                record.coordinates_display = 'Chưa có tọa độ'
    
    @api.depends('latitude', 'longitude')
    def _compute_google_maps_url(self):
        """Tạo link Google Maps"""
        for record in self:
            if record.latitude and record.longitude:
                record.google_maps_url = f'https://www.google.com/maps?q={record.latitude},{record.longitude}'
            else:
                record.google_maps_url = False
    
    @api.constrains('latitude', 'longitude')
    def _check_coordinates(self):
        """Validate tọa độ GPS"""
        for record in self:
            if record.latitude:
                if not -90 <= record.latitude <= 90:
                    raise ValidationError(_('Vĩ độ phải nằm trong khoảng -90 đến 90'))
            if record.longitude:
                if not -180 <= record.longitude <= 180:
                    raise ValidationError(_('Kinh độ phải nằm trong khoảng -180 đến 180'))
    
    @api.constrains('is_default')
    def _check_single_default(self):
        """Chỉ cho phép 1 địa điểm mặc định"""
        for record in self:
            if record.is_default:
                other_defaults = self.search([
                    ('is_default', '=', True),
                    ('id', '!=', record.id)
                ])
                if other_defaults:
                    other_defaults.write({'is_default': False})
    
    def action_view_attendances(self):
        """Xem danh sách chấm công tại địa điểm này"""
        self.ensure_one()
        return {
            'name': _('Chấm công - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'hr.attendance',
            'view_mode': 'list,form',
            'domain': [('work_location_id', '=', self.id)],
            'context': {'search_default_today': 1}
        }
    
    def action_open_google_maps(self):
        """Mở Google Maps"""
        self.ensure_one()
        if not self.google_maps_url:
            raise ValidationError(_('Địa điểm này chưa có tọa độ GPS!'))
        
        return {
            'type': 'ir.actions.act_url',
            'url': self.google_maps_url,
            'target': 'new',
        }
