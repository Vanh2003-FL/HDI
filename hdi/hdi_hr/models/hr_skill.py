# -*- coding: utf-8 -*-

from odoo import fields, models


class HrSkill(models.Model):
    _inherit = 'hr.skill'

    hdi_skill_category = fields.Selection([
        ('technical', 'Kỹ thuật'),
        ('soft', 'Kỹ năng mềm'),
        ('language', 'Ngoại ngữ'),
        ('management', 'Quản lý'),
        ('other', 'Khác'),
    ], string='Loại kỹ năng', default='technical')
    
    hdi_is_mandatory = fields.Boolean(
        string='Bắt buộc',
        default=False,
        help='Kỹ năng bắt buộc cho vị trí'
    )
