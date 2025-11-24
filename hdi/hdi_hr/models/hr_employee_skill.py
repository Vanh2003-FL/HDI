# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HdiSkill(models.Model):
    """Danh mục kỹ năng"""
    _name = 'hdi.skill'
    _description = 'HDI Kỹ năng'
    _order = 'name'

    name = fields.Char(string='Tên kỹ năng', required=True, translate=True)
    skill_type_id = fields.Many2one('hdi.skill.type', string='Loại kỹ năng', ondelete='cascade')
    description = fields.Text(string='Mô tả')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Tên kỹ năng phải là duy nhất!'),
    ]


class HdiSkillType(models.Model):
    """Loại kỹ năng"""
    _name = 'hdi.skill.type'
    _description = 'HDI Loại kỹ năng'
    _order = 'name'

    name = fields.Char(string='Tên loại', required=True, translate=True)
    skill_ids = fields.One2many('hdi.skill', 'skill_type_id', string='Kỹ năng')
    skill_count = fields.Integer(string='Số lượng', compute='_compute_skill_count')
    active = fields.Boolean(string='Hoạt động', default=True)

    @api.depends('skill_ids')
    def _compute_skill_count(self):
        for skill_type in self:
            skill_type.skill_count = len(skill_type.skill_ids)


class HdiEmployeeSkill(models.Model):
    """Kỹ năng của nhân viên"""
    _name = 'hdi.employee.skill'
    _description = 'HDI Kỹ năng nhân viên'
    _rec_name = 'skill_id'

    employee_id = fields.Many2one('hr.employee', string='Nhân viên', required=True, ondelete='cascade')
    skill_id = fields.Many2one('hdi.skill', string='Kỹ năng', required=True)
    skill_type_id = fields.Many2one('hdi.skill.type', string='Loại kỹ năng', related='skill_id.skill_type_id', store=True)
    
    hdi_proficiency_level = fields.Selection([
        ('1', 'Cơ bản'),
        ('2', 'Trung bình'),
        ('3', 'Khá'),
        ('4', 'Giỏi'),
        ('5', 'Xuất sắc'),
    ], string='Trình độ', default='1', required=True)
    
    hdi_certification = fields.Char(
        string='Chứng chỉ',
        help='Chứng chỉ liên quan đến kỹ năng'
    )
    
    hdi_years_of_experience = fields.Float(
        string='Số năm kinh nghiệm',
        default=0.0
    )
    
    hdi_last_assessed_date = fields.Date(string='Ngày đánh giá gần nhất')
    hdi_assessed_by = fields.Many2one('res.users', string='Người đánh giá')
    hdi_notes = fields.Text(string='Ghi chú')

    @api.constrains('hdi_years_of_experience')
    def _check_years_of_experience(self):
        """Kiểm tra số năm kinh nghiệm hợp lệ"""
        for skill in self:
            if skill.hdi_years_of_experience < 0:
                raise ValidationError(_('Số năm kinh nghiệm phải lớn hơn hoặc bằng 0!'))
