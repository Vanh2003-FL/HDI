# -*- coding: utf-8 -*-

from odoo import fields, models


class HrJob(models.Model):
    _inherit = 'hr.job'

    hdi_job_code = fields.Char(string='Mã vị trí', required=True)
    hdi_job_level = fields.Selection([
        ('entry', 'Nhân viên'),
        ('senior', 'Nhân viên cao cấp'),
        ('leader', 'Trưởng nhóm'),
        ('manager', 'Quản lý'),
        ('director', 'Giám đốc'),
    ], string='Cấp bậc', default='entry')
    
    hdi_required_skills = fields.Many2many(
        'hdi.skill',
        'hdi_job_skill_rel',
        'job_id',
        'skill_id',
        string='Kỹ năng yêu cầu'
    )
    
    hdi_min_experience = fields.Float(
        string='Kinh nghiệm tối thiểu (năm)',
        default=0.0
    )
