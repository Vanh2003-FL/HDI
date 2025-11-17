# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class HrWorkLocation(models.Model):
    _name = 'hr.work.location'
    _description = 'Địa điểm làm việc'
    _order = 'name'

    name = fields.Char(
        string='Tên địa điểm',
        required=True
    )
    
    code = fields.Char(
        string='Mã địa điểm',
        help='Mã viết tắt cho địa điểm'
    )
    
    address = fields.Text(
        string='Địa chỉ',
        required=True
    )
    
    latitude = fields.Float(
        string='Vĩ độ',
        digits=(10, 7),
        help='Tọa độ vĩ độ của địa điểm'
    )
    
    longitude = fields.Float(
        string='Kinh độ',
        digits=(10, 7),
        help='Tọa độ kinh độ của địa điểm'
    )
    
    # Settings
    is_active = fields.Boolean(
        string='Hoạt động',
        default=True
    )
    
    is_default = fields.Boolean(
        string='Mặc định',
        help='Địa điểm làm việc mặc định cho công ty'
    )
    
    allowed_checkin_radius = fields.Float(
        string='Bán kính check-in cho phép (m)',
        default=100.0,
        help='Bán kính tối đa cho phép check-in tại địa điểm này (mét)'
    )
    
    allowed_checkout_radius = fields.Float(
        string='Bán kính check-out cho phép (m)',
        default=500.0,
        help='Bán kính tối đa cho phép check-out tại địa điểm này (mét)'
    )
    
    # Relations
    company_id = fields.Many2one(
        'res.company',
        string='Công ty',
        default=lambda self: self.env.company
    )
    
    employee_ids = fields.Many2many(
        'hr.employee',
        'employee_work_location_rel',
        'location_id',
        'employee_id',
        string='Nhân viên được phép',
        help='Danh sách nhân viên được phép làm việc tại địa điểm này'
    )
    
    # Statistics
    total_checkins = fields.Integer(
        string='Tổng số check-in',
        compute='_compute_attendance_stats'
    )
    
    total_checkouts = fields.Integer(
        string='Tổng số check-out',
        compute='_compute_attendance_stats'
    )
    
    today_checkins = fields.Integer(
        string='Check-in hôm nay',
        compute='_compute_today_stats'
    )
    
    today_checkouts = fields.Integer(
        string='Check-out hôm nay',
        compute='_compute_today_stats'
    )
    
    # Work schedule
    work_schedule_ids = fields.One2many(
        'work.location.schedule',
        'location_id',
        string='Lịch làm việc'
    )
    
    # Contact info
    contact_person = fields.Char(
        string='Người liên hệ',
        help='Người phụ trách tại địa điểm này'
    )
    
    contact_phone = fields.Char(
        string='Số điện thoại liên hệ'
    )
    
    contact_email = fields.Char(
        string='Email liên hệ'
    )
    
    # Description
    description = fields.Text(
        string='Mô tả',
        help='Mô tả chi tiết về địa điểm làm việc'
    )
    
    # Map URL
    google_maps_url = fields.Char(
        string='Google Maps URL',
        compute='_compute_google_maps_url',
        store=True
    )

    @api.depends('latitude', 'longitude')
    def _compute_google_maps_url(self):
        """Tạo Google Maps URL từ tọa độ"""
        for location in self:
            if location.latitude and location.longitude:
                location.google_maps_url = f"https://www.google.com/maps/place/{location.latitude},{location.longitude}"
            else:
                location.google_maps_url = ""

    @api.depends('employee_ids.attendance_ids')
    def _compute_attendance_stats(self):
        """Tính thống kê chấm công tại địa điểm"""
        for location in self:
            checkin_count = self.env['hr.attendance'].search_count([
                ('hdi_work_location_id', '=', location.id)
            ])
            checkout_count = self.env['hr.attendance'].search_count([
                ('hdi_checkout_location_id', '=', location.id)
            ])
            location.total_checkins = checkin_count
            location.total_checkouts = checkout_count

    def _compute_today_stats(self):
        """Tính thống kê hôm nay"""
        today = fields.Date.today()
        for location in self:
            today_checkin_count = self.env['hr.attendance'].search_count([
                ('hdi_work_location_id', '=', location.id),
                ('check_in_date', '=', today)
            ])
            today_checkout_count = self.env['hr.attendance'].search_count([
                ('hdi_checkout_location_id', '=', location.id),
                ('check_out_date', '=', today)
            ])
            location.today_checkins = today_checkin_count
            location.today_checkouts = today_checkout_count

    @api.constrains('is_default')
    def _check_default_location(self):
        """Đảm bảo chỉ có 1 địa điểm mặc định"""
        if self.is_default:
            other_defaults = self.search([
                ('id', '!=', self.id),
                ('is_default', '=', True),
                ('company_id', '=', self.company_id.id)
            ])
            if other_defaults:
                other_defaults.write({'is_default': False})

    def name_get(self):
        """Customize display name"""
        result = []
        for location in self:
            name = location.name
            if location.code:
                name = f"[{location.code}] {name}"
            result.append((location.id, name))
        return result

    def action_view_attendances(self):
        """Xem danh sách chấm công tại địa điểm"""
        return {
            'name': _('Chấm công tại %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'hr.attendance',
            'view_mode': 'tree,form,calendar',
            'domain': [
                '|',
                ('hdi_work_location_id', '=', self.id),
                ('hdi_checkout_location_id', '=', self.id)
            ],
            'context': {
                'search_default_location_id': self.id,
            }
        }

    def action_open_map(self):
        """Mở bản đồ Google Maps"""
        if self.google_maps_url:
            return {
                'type': 'ir.actions.act_url',
                'url': self.google_maps_url,
                'target': 'new',
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Thông báo'),
                    'message': _('Chưa có thông tin tọa độ GPS để mở bản đồ'),
                    'type': 'warning',
                }
            }

    def get_distance_from(self, latitude, longitude):
        """Tính khoảng cách từ tọa độ đến địa điểm này"""
        if not (self.latitude and self.longitude and latitude and longitude):
            return 0.0
            
        import math
        
        # Convert to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [latitude, longitude, self.latitude, self.longitude])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Earth radius in meters
        r = 6371000
        
        return r * c

    def is_within_checkin_radius(self, latitude, longitude):
        """Kiểm tra có trong bán kính check-in không"""
        distance = self.get_distance_from(latitude, longitude)
        return distance <= self.allowed_checkin_radius

    def is_within_checkout_radius(self, latitude, longitude):
        """Kiểm tra có trong bán kính check-out không"""
        distance = self.get_distance_from(latitude, longitude)
        return distance <= self.allowed_checkout_radius


class WorkLocationSchedule(models.Model):
    _name = 'work.location.schedule'
    _description = 'Lịch làm việc theo địa điểm'
    _order = 'location_id, dayofweek, hour_from'

    location_id = fields.Many2one(
        'hr.work.location',
        string='Địa điểm',
        required=True,
        ondelete='cascade'
    )
    
    name = fields.Char(
        string='Tên ca',
        required=True
    )
    
    dayofweek = fields.Selection([
        ('0', 'Thứ 2'),
        ('1', 'Thứ 3'),
        ('2', 'Thứ 4'),
        ('3', 'Thứ 5'),
        ('4', 'Thứ 6'),
        ('5', 'Thứ 7'),
        ('6', 'Chủ nhật'),
    ], string='Ngày trong tuần', required=True)
    
    hour_from = fields.Float(
        string='Giờ bắt đầu',
        required=True
    )
    
    hour_to = fields.Float(
        string='Giờ kết thúc',
        required=True
    )
    
    is_active = fields.Boolean(
        string='Hoạt động',
        default=True
    )

    @api.constrains('hour_from', 'hour_to')
    def _check_hours(self):
        """Validate working hours"""
        for schedule in self:
            if schedule.hour_from >= schedule.hour_to:
                raise UserError(_('Giờ kết thúc phải sau giờ bắt đầu!'))