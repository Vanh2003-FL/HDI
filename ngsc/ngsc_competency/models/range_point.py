# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from ..constants.constants import STATUS_ACTIVE, STATUS_INACTIVE


class RangePoint(models.Model):
    _name = 'ngsc.competency.range.point'
    _description = 'Thang điểm'

    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string=u'Tên thang điểm', help=u'tên thang điểm', required=True, tracking=True)
    code = fields.Char(string=u'Mã thang điêm', help=u'mã thang điểm', unique=True, readonly=True, tracking=True)
    level = fields.Integer(string=u'Số mức độ đánh giá', help=u'số mức độ đánh giá (1->5..)', compute='_compute_level', store=True, readonly=True, tracking=True)
    active = fields.Boolean(string=u'Hoạt động', help=u'trạng thái hoạt động', default=True)
    description = fields.Text(string=u'Mô tả', help=u'mô tả', tracking=True)

    skill_group_ids = fields.One2many(string=u'nhóm kỹ năng', comodel_name='ngsc.competency.skill.group',
                                      inverse_name='range_point_id', tracking=True)
    level_ids = fields.One2many(string=u'Mức độ', comodel_name='ngsc.competency.level',
                                inverse_name='range_point_id', tracking=True)

    active_display = fields.Char(
        string=u'Trạng thái',
        compute='_compute_active_display',
        tracking=True, store=True
    )

    @api.depends('active')
    def _compute_active_display(self):
        for record in self:
            record.active_display = STATUS_ACTIVE if record.active else STATUS_INACTIVE


    @api.depends('level_ids')
    def _compute_level(self):
        for record in self:
            record.level = len(record.level_ids)

    @api.model
    def create(self, vals):
        vals['code'] = self.env['ir.sequence'].next_by_code('ngsc.competency.range.point')
        return super(RangePoint, self).create(vals)

    def write(self, vals):
        if 'active' in vals and not vals['active']:
            for record in self:
                # Check if the range point is linked to any skill group
                if record.skill_group_ids:
                    skill_group_names = '\n- '.join(record.skill_group_ids.mapped('name'))
                    raise ValidationError(
                        f"Hiện hệ thống đang phát hiện có {len(record.skill_group_ids)} Nhóm kỹ năng đang sử dụng Thang điểm này, "
                        f"đề nghị kiểm tra lại hoặc đóng trạng thái các Nhóm kỹ năng liên quan để tiếp tục:\n "
                        f"- {skill_group_names}"
                    )
        res = super(RangePoint, self).write(vals)

        # Nếu level_ids được cập nhật (có thể bao gồm xóa)
        if 'level_ids' in vals:
            # Lấy tất cả Level còn lại
            levels = self.level_ids.sorted(key=lambda l: l.sequence)
            # Cập nhật sequence tăng dần từ 1
            for index, level in enumerate(levels, 1):
                if level.sequence != index:
                    level.write({'sequence': index})

        return res
