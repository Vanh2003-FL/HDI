# -*- coding: utf-8 -*-
from odoo import models, fields


class HrWorkLocation(models.Model):
    _name = 'hr.work.location'
    _description = 'Work Location'
    _order = 'name'
    
    name = fields.Char(string='Tên địa điểm', required=True)
    address = fields.Char(string='Địa chỉ')
    latitude = fields.Float(string='Vĩ độ', digits=(10, 7))
    longitude = fields.Float(string='Kinh độ', digits=(10, 7))
    radius = fields.Integer(string='Bán kính cho phép (m)', default=100,
                             help='Bán kính tính bằng mét cho phép chấm công từ vị trí này')
    active = fields.Boolean(string='Hoạt động', default=True)
    company_id = fields.Many2one('res.company', string='Công ty', 
                                  default=lambda self: self.env.company)
