# -*- coding: utf-8 -*-
from odoo import models, fields, api, _, exceptions
from odoo.exceptions import ValidationError


class NgscCandidateSearchLine(models.Model):
    _name = "ngsc.candidate.search.line"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Tham số kỹ năng tìm kiếm nhân sự"

    candidate_search_id = fields.Many2one("ngsc.candidate.search", string="Tìm kiếm nguồn lực nhân sự", tracking=True)
    skill_id = fields.Many2one("ngsc.competency.skill", string="Kỹ năng", required=True, tracking=True)
    skill_group_id = fields.Many2one("ngsc.competency.skill.group", string="Nhóm kỹ năng",
                                     related="skill_id.skill_group_id", readonly=True, store=True)
    level_id = fields.Many2one("ngsc.competency.skill.level", string="Mức độ",
                               domain="[('skill_id', '=', skill_id)]", tracking=True)
    priority = fields.Boolean(string="Ưu tiên", default=False, tracking=True)
    weight = fields.Integer(string="Trọng số", default=0, tracking=True)
    score = fields.Float(string="Điểm kỹ năng", compute="_compute_score", store=True)

    @api.onchange('weight')
    def _onchange_weight(self):
        for rec in self:
            if rec.weight > 100:
                rec.weight = 0  # reset về 0
                raise ValidationError("Trọng số vượt 100%. Yêu cầu nhập lại.")
            elif rec.weight <= 0:
                raise ValidationError("Trọng số phải lớn hơn 0%. Yêu cầu nhập lại.")

    @api.constrains('weight')
    def _onchange_weight(self):
        for rec in self:
            if rec.weight <= 0:
                raise ValidationError("Trọng số phải lớn hơn 0%. Yêu cầu nhập lại.")

    @api.constrains('level_id')
    def _check_level_required(self):
        for rec in self:
            if not rec.level_id:
                raise ValidationError("Trường mức độ không được để trống. Yêu cầu nhập lại.")

    @api.depends("level_id", "weight")
    def _compute_score(self):
        for rec in self:
            if rec.level_id.sequence >= 0 and rec.weight >= 0:
                rec.score = rec.level_id.sequence * rec.weight / 100
            else:
                rec.score = 0
