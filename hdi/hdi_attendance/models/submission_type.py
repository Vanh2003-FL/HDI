# -*- coding: utf-8 -*-
from odoo import models, fields


class SubmissionType(models.Model):
    _name = 'submission.type'
    _description = 'Loại giải trình'
    _order = 'sequence, name'
    
    name = fields.Char(string='Tên loại giải trình', required=True, translate=True)
    code = fields.Char(string='Mã', required=True)
    sequence = fields.Integer(string='Thứ tự', default=10)
    active = fields.Boolean(string='Hoạt động', default=True)
    description = fields.Text(string='Mô tả', translate=True)
    mark_count = fields.Boolean(
        string='Tính vào số lần giải trình',
        default=True,
        help='Nếu bật, loại giải trình này sẽ được tính vào giới hạn số lần giải trình/tháng'
    )
    used_explanation_date = fields.Boolean(
        string='Sử dụng Ngày giải trình',
        default=False,
        help='Nếu bật, sẽ sử dụng trường "Ngày giải trình" thay vì "Bản ghi chấm công"'
    )
    
    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Mã loại giải trình phải là duy nhất!')
    ]
