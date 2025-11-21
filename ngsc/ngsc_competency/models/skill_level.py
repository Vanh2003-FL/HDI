# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class SkillLevel(models.Model):
    _name = 'ngsc.competency.skill.level'
    _rec_name = 'name'
    _order = 'sequence asc'
    _description = 'Bảng quan hệ mô tả các mức độ cho skill'

    detail = fields.Text(string=u'Chi tiết')

    skill_id = fields.Many2one(string=u'Kỹ năng', comodel_name='ngsc.competency.skill', ondelete='cascade')
    level_id = fields.Many2one(string=u'Mức độ', comodel_name='ngsc.competency.level', ondelete='cascade')

    # Thêm field related
    name = fields.Char(string="Tên mức độ", compute="_compute_sequence", store=True)
    description = fields.Text(string="Mô tả mức độ", compute="_compute_sequence", store=True)
    sequence = fields.Integer(string="Cấp độ", compute="_compute_sequence", store=True)

    @api.depends("level_id", "level_id.sequence", "level_id.description", "level_id.name")
    def _compute_sequence(self):
        for rec in self:
            rec.sequence = rec.level_id.sequence
            rec.name = rec.level_id.name
            rec.name = f"{rec.level_id.sequence or ''} - {rec.level_id.name or ''}"
            rec.description = rec.level_id.description
