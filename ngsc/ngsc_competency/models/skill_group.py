# -*- coding: utf-8 -*-
from datetime import datetime
from odoo.exceptions import UserError, ValidationError
from odoo import models, fields, api, _, exceptions

from ..constants.constants import STATUS_ACTIVE, STATUS_INACTIVE


class SkillGroup(models.Model):
    _name = 'ngsc.competency.skill.group'
    _description = 'Nhóm các kỹ năng'
    _rec_name = 'name'

    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string=u'Tên nhóm kỹ năng', help=u'Tên nhóm kỹ năng', required=True, tracking=True)
    code = fields.Char(string=u'Mã nhóm kỹ năng', help=u'Mã nhóm kỹ năng', unique=True, tracking=True)
    short_name = fields.Char(string=u'Tên viết tắt', help=u'Tên viết tắt', unique=True, required=True, tracking=True)
    active = fields.Boolean(string=u'Hoạt động', help=u'Trạng thái hoạt động', default=True)
    description = fields.Text(string=u'Mô tả', help=u'Mô tả', tracking=True)

    range_point_id = fields.Many2one(comodel_name='ngsc.competency.range.point', string=u'Thang điểm', required=True, tracking=True)
    tag_ids = fields.One2many(string=u'Nhóm kỹ năng', comodel_name='ngsc.competency.tag',
                              inverse_name='skill_group_id', tracking=True)
    active_display = fields.Char(
        string=u'Trạng thái',
        compute='_compute_active_display',
        tracking=True, store=True
    )
    write_date_formatted = fields.Char(string='Ngày cập nhật', compute='_compute_write_date_formatted')
    level_ids = fields.One2many(related='range_point_id.level_ids', string='Mức độ', readonly=True, tracking=True)
    skill_ids = fields.One2many('ngsc.competency.skill', 'skill_group_id', string='Kỹ năng')

    @api.depends('active')
    def _compute_active_display(self):
        for record in self:
            record.active_display = STATUS_ACTIVE if record.active else STATUS_INACTIVE

    @api.depends('write_date')
    def _compute_write_date_formatted(self):
        for record in self:
            if record.write_date:
                record.write_date_formatted = datetime.strftime(record.write_date, '%d/%m/%Y')
            else:
                record.write_date_formatted = ''

    @api.model
    def create(self, vals):
        vals['code'] = self.env['ir.sequence'].next_by_code('ngsc.competency.skill.group')
        return super(SkillGroup, self).create(vals)

    def write(self, vals):
        if 'active' in vals and not vals['active']:
            for record in self:
                if record.tag_ids:
                    tag_names = '\n- '.join(record.tag_ids.mapped('name'))
                    raise ValidationError(
                        f"Hiện hệ thống phát hiện có {len(record.tag_ids)} Thẻ gắn với Nhóm kỹ năng, "
                        f"đề nghị kiểm tra lại hoặc đóng trạng thái các Nhóm kỹ năng liên quan để tiếp tục:\n- {tag_names}"
                    )

        # Thay đổi thang điểm thì xoá thông tin SkillLevel cũ -> tạo bản ghi SkillLevel mới
        if 'range_point_id' in vals and self.range_point_id != vals['range_point_id']:
            skill_ids = self.mapped('skill_ids').ids
            # Xoá tất cả SkillLevel theo skill_ids
            if skill_ids:
                (self.env['ngsc.competency.skill.level']
                 .search([('skill_id', 'in', skill_ids)])  # Tìm kiếm
                 .unlink())  # Xoá

            # Tìm level_ids thuộc range_point_id mới
            level_ids = self.env['ngsc.competency.level'].search(
                [('range_point_id', '=', vals['range_point_id'])]).ids

            # Tạo danh sách SkillLevel từ skill_ids và level_ids
            skill_level_vals = [
                {'skill_id': skill_id, 'level_id': level_id, 'detail': ''}
                for skill_id in skill_ids for level_id in level_ids
            ]
            self.env['ngsc.competency.skill.level'].create(skill_level_vals)

        return super(SkillGroup, self).write(vals)

    # ✅ Hiển thị short_name - name
    def name_get(self):
        result = []
        for record in self:
            display_name = f"{record.short_name or ''} - {record.name or ''}"
            result.append((record.id, display_name))
        return result

    # ✅ Tìm theo short_name, code, name + Ưu tiên kết quả bắt đầu bằng từ khóa
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []

        domain = ['|', '|',
                  ('short_name', operator, name),
                  ('code', operator, name),
                  ('name', operator, name)]
        records = self.search(domain + args)

        def priority(record):
            key = (name or '').lower()
            score = 0
            if record.short_name and record.short_name.lower().startswith(key):
                score -= 10
            if record.code and record.code.lower().startswith(key):
                score -= 5
            if record.name and record.name.lower().startswith(key):
                score -= 2
            return score, (record.short_name or ''), (record.name or '')

        sorted_records = sorted(records, key=priority)

        return [(r.id, f"{r.short_name or ''} - {r.name or ''}") for r in sorted_records[:limit]]
