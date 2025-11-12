# -*- coding: utf-8 -*-
from odoo import models, fields, api


class HrEmployeeSkills(models.Model):
    _inherit = 'hr.employee.skills'

    current_level_id = fields.Many2one("ngsc.competency.skill.level", string="Mức độ hiện tại",
                                       domain="[('skill_id', '=', skill_id)]", tracking=True)
    sequence = fields.Integer(string="Cấp độ", compute="_compute_current_level_sequence", store=True)

    @api.depends("current_level_id", "current_level_id.sequence")
    def _compute_current_level_sequence(self):
        for rec in self:
            rec.sequence = rec.current_level_id.sequence if rec.current_level_id else 0
