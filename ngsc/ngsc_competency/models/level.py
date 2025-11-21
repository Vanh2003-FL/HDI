# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class Level(models.Model):
    _name = 'ngsc.competency.level'
    _order = 'sequence asc'
    _description = 'Mức độ'

    name = fields.Char(string=u'Tên mức độ', help=u'tên mức độ', required=True)
    sequence = fields.Integer(string=u'Vị trí sắp xếp', help=u'Vị trí sắp xếp', default=True, tracking=True)
    description = fields.Text(string=u'Mô tả', help=u'mô tả', tracking=True)

    range_point_id = fields.Many2one(comodel_name='ngsc.competency.range.point', string=u'Thang điểm')
    skill_ids = fields.Many2many(comodel_name='ngsc.competency.skill', relation='skill_level_rel',
                                 column1='ngsc_competency_level_id', column2='ngsc_competency_skill_id',
                                 string=u'Kỹ năng', through='ngsc.competency.skill.level')
    sq_order = fields.Integer(string=u'Cấp độ', compute='_compute_order', readonly=True, store=False)

    def _compute_order(self):
        for record in self:
            record.sq_order = record.sequence


    @api.model
    def create(self, values):
        range_point_id = values.get('range_point_id')
        if range_point_id:
            # Đếm số Level hiện có của range_point_id
            existing_levels = self.env['ngsc.competency.level'].search_count([
                ('range_point_id', '=', range_point_id)
            ])
            # Gán sequence tăng dần (1, 2, 3, ...)
            values['sequence'] = existing_levels + 1

        res = super().create(values)

        # Kiểm tra xem range_point_id có tồn tại không
        if res.range_point_id:
            # Lấy danh sách skill_group_ids từ RangePoint
            skill_groups = res.range_point_id.skill_group_ids
            if skill_groups:
                # Lấy tất cả skill_ids từ các SkillGroup
                skill_ids = skill_groups.mapped('skill_ids').ids
                if skill_ids:
                    # Tạo các bản ghi SkillLevel
                    skill_level_vals = [
                        {
                            'level_id': res.id,  # ID của Level vừa tạo
                            'skill_id': skill_id,  # ID của từng Skill
                            'detail': '',  # Giá trị mặc định cho detail
                        }
                        for skill_id in skill_ids
                    ]
                    self.env['ngsc.competency.skill.level'].create(skill_level_vals)

        return res
