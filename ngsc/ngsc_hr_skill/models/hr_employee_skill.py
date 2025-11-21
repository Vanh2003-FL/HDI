# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class HrEmployeeSkills(models.Model):
    _name = 'hr.employee.skills'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'skill_id'
    _order = 'skill_group_id asc'
    _description = 'Bảng quan hệ mô tả các kỹ năng của nhân viên'

    skill_id = fields.Many2one("ngsc.competency.skill", string="Tên kỹ năng", required=True, tracking=True)
    expected_level_id = fields.Many2one("ngsc.competency.skill.level", string="Mức độ kỳ vọng",
                                        domain="[('skill_id', '=', skill_id)]", tracking=True)
    current_level_id = fields.Many2one("ngsc.competency.skill.level", string="Mức độ hiện tại",
                                       domain="[('skill_id', '=', skill_id)]", tracking=True)
    skill_group_id = fields.Many2one("ngsc.competency.skill.group", string="Nhóm kỹ năng",
                                     related="skill_id.skill_group_id", readonly=True, store=True)
    short_name = fields.Char(string="Tên viết tắt", related="skill_id.short_name", readonly=True, store=True)
    tag_id = fields.Many2one("ngsc.competency.tag", string="Thẻ", related="skill_id.tag_id", readonly=True, store=True)
    tag_color_code = fields.Integer(string=u'Mã màu thẻ', related='tag_id.color_code', readonly=True, tracking=False)
    description = fields.Text(string="Mô tả", related="skill_id.description", readonly=True, store=True)
    code = fields.Char(string="Mã kỹ năng", related="skill_id.code", readonly=True, store=True)
    hr_employee_id = fields.Many2one("hr.employee", string="Nhân viên", tracking=True)
    competency_level_count = fields.Integer(string="Số lượng mức độ", compute="_compute_competency_level")
    level_steps = fields.Char(string="Danh sách ID các mức độ", compute="_compute_level_steps")
    level_current = fields.Integer(string="Mức độ")
    skill_level_ids = fields.Many2many("ngsc.competency.skill.level", "hr_employee_skill_level_rel", "employee_id",
                                       "level_id", compute='_compute_competency_level_ids',
                                       string='Các mức độ kỹ năng', store=False)

    def _compute_competency_level_ids(self):
        for rec in self:
            rec.skill_level_ids = rec.skill_id.level_ids

    def _compute_competency_level(self):
        for rec in self:
            rec.competency_level_count = len(rec.skill_id.level_ids)

    def _compute_level_steps(self):
        for rec in self:
            if rec.skill_id.level_ids:
                rec.level_steps = ",".join(map(str, rec.skill_id.level_ids.sorted(key="sequence").mapped("name")))
            else:
                rec.level_steps = ""

    # Open form view detail
    def action_open_view_detail(self):
        return {
            'name': "Chi tiết thông tin năng lực",
            'view_mode': 'form',
            'res_model': 'hr.employee.skills',
            'type': 'ir.actions.act_window',
            'view_id': self.env.ref('ngsc_hr_skill.hr_employee_skills_view_form').id,
            'views': [(self.env.ref('ngsc_hr_skill.hr_employee_skills_view_form').id, 'form')],
            'res_id': self.id,
            'target': 'current',
        }

    def action_view_list_competency_level(self):
        return {
            'name': "Mức độ năng lực",
            'view_mode': 'tree',
            'res_model': 'ngsc.competency.skill.level',
            'type': 'ir.actions.act_window',
            'view_id': self.env.ref('ngsc_hr_skill.ngsc_competency_skill_level_view_tree').id,
            'views': [(self.env.ref('ngsc_hr_skill.ngsc_competency_skill_level_view_tree').id, 'tree'),
                      (False, 'form')],
            'domain': [('id', 'in', self.skill_id.level_ids.ids)],
            'target': 'current',
        }
