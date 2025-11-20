# -*- coding: utf-8 -*-
from odoo import models, fields


class SubmissionType(models.Model):
    _name = 'submission.type'
    _description = 'Submission Type'
    _order = 'sequence, name'
    
    name = fields.Char(string='Tên loại giải trình', required=True, translate=True)
    code = fields.Char(string='Mã', required=True)
    sequence = fields.Integer(string='Thứ tự', default=10)
    active = fields.Boolean(string='Hoạt động', default=True)
    description = fields.Text(string='Mô tả', translate=True)
    used_explanation_date = fields.Boolean(
        string='Sử dụng ngày giải trình',
        default=True,
        help='Nếu bật, sẽ hiển thị trường Ngày giải trình trong form'
    )
    
    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Mã loại giải trình phải là duy nhất!')
    ]
