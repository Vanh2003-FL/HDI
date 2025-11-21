# -*- coding: utf-8 -*-
from odoo import models, fields, api, _, exceptions
from odoo.exceptions import ValidationError
from ..constants.constants import STATUS_ACTIVE, STATUS_INACTIVE


class Skill(models.Model):
    _name = 'ngsc.competency.skill'
    _description = 'Các kỹ năng'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    COMMAND_CREATE = 0
    COMMAND_UPDATE = 1

    name = fields.Char(string=u'Tên kỹ năng', help=u'tên kỹ năng', required=True, tracking=True)
    code = fields.Char(string=u'Mã kỹ năng', help=u'mã kỹ năng', unique=True, readonly=True, copy=False)
    short_name = fields.Char(string=u'Tên viết tắt', help=u'Tên viết tắt', unique=True, tracking=True)
    active = fields.Boolean(string=u'Hoạt động', help=u'trạng thái hoạt động', default=True)
    description = fields.Text(string=u'Mô tả', help=u'mô tả', tracking=True)

    skill_group_id = fields.Many2one(string=u'Nhóm kỹ năng', comodel_name='ngsc.competency.skill.group', tracking=True)
    tag_id = fields.Many2one(string=u'Thẻ', comodel_name='ngsc.competency.tag', tracking=True)
    level_ids = fields.One2many("ngsc.competency.skill.level", "skill_id", string="Mức độ")

    # Thêm field related để lấy tên nhóm kỹ năng
    skill_group_name = fields.Char(string=u'Nhóm kỹ năng', related='skill_group_id.name', readonly=True)
    tag_color_code = fields.Integer(string=u'Mã màu thẻ', related='tag_id.color_code', readonly=True, tracking=False)
    active_status = fields.Char(string=u'Trạng thái', compute='_compute_active_status', tracking=True, store=True)

    @api.onchange('skill_group_id')
    def _onchange_skill_group(self):
        if not self._context.get('import_file', False):
            self.tag_id = False
        self.level_ids = False
        skill_id = self.id or self._origin.id
        if self.skill_group_id and self.skill_group_id.range_point_id:
            range_levels = self.skill_group_id.range_point_id.level_ids
            if skill_id:  # Nếu Skill đã tồn tại
                skill_levels = self.env['ngsc.competency.skill.level'].search([
                    ('skill_id', '=', skill_id),
                    ('level_id', 'in', range_levels.ids),
                ])
                level_dict = {sl.level_id.id: sl.detail for sl in skill_levels}
                commands = []
                for level in range_levels:
                    detail = level_dict.get(level.id, "")
                    commands.append((0, 0, {
                        'level_id': level.id,
                        'detail': detail,
                    }))

                self.level_ids = commands
            else:  # Nếu Skill chưa tồn tại
                commands = [(0, 0, {
                    'level_id': level.id,
                    'detail': "",
                }) for level in range_levels]
                self.level_ids = commands

    @api.depends('active')
    def _compute_active_status(self):
        for record in self:
            record.active_status = STATUS_ACTIVE if record.active else STATUS_INACTIVE

    @api.model
    def create(self, vals):
        # if not vals.get('code'):  # Chỉ tạo mã nếu chưa có giá trị
        vals['code'] = self.env['ir.sequence'].next_by_code('ngsc.competency.skill.code')
        if 'level_ids' in vals:
            for command in vals['level_ids']:
                if command[0] == self.COMMAND_CREATE or command[0] == self.COMMAND_UPDATE:  # (0: create, 1: update)
                    detail = command[2].get('detail')
                    if not detail:
                        raise ValidationError(
                            _("Trường 'Chi tiết' trong 'Mức độ' là bắt buộc. Vui lòng điền đầy đủ thông tin."))
        res = super(Skill, self).create(vals)
        return res

    def copy(self, default=None):
        default = default or {}
        new_skill = super(Skill, self).copy(default)
        for level in self.level_ids:
            # Copy o2m and assign new project
            level.copy(default={'skill_id': new_skill.id})
        return new_skill

    def write(self, vals):
        if 'level_ids' in vals:
            for command in vals['level_ids']:
                if command[0] == self.COMMAND_CREATE or command[0] == self.COMMAND_UPDATE:
                    detail = command[2].get('detail')
                    if not detail:
                        raise ValidationError(
                            _("Trường 'Chi tiết' trong 'Mức độ' là bắt buộc. Vui lòng điền đầy đủ thông tin."))
        else:
            for record in self:
                missing_levels = record.level_ids.filtered(lambda l: not l.detail)
                if missing_levels:
                    level_names = ", ".join(missing_levels.mapped('level_id.name'))
                    raise ValidationError(
                        _("Trường 'Chi tiết' là bắt buộc cho các mức độ: %s. Vui lòng điền đầy đủ thông tin.") % level_names
                    )
        return super(Skill, self).write(vals)


    @api.constrains('name', 'skill_group_id')
    def _check_unique_skill_name_per_group(self):
        for record in self:
            if record.name and record.skill_group_id:
                duplicates = self.search([
                    ('name', '=', record.name),
                    ('skill_group_id', '=', record.skill_group_id.id),
                    ('id', '!=', record.id)
                ], limit=1)
                if duplicates:
                    raise ValidationError(
                        f"Tên kỹ năng '{record.name}' đã tồn tại trong nhóm kỹ năng '{record.skill_group_id.name}'."
                    )