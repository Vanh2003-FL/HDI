# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from ..constants.constants import STATUS_ACTIVE, STATUS_INACTIVE

COLOR_SELECTION = [
    ('0', 'Không có màu'),
    ('1', 'Đỏ'),
    ('2', 'Cam'),
    ('3', 'Vàng'),
    ('4', 'Xanh da trời nhạt'),
    ('5', 'Tím đậm'),
    ('6', 'Hồng nhạt'),
    ('7', 'Xanh lam'),
    ('8', 'Xanh đậm'),
    ('9', 'Hồng tím'),
    ('10', 'Xanh lá cây'),
    ('11', 'Tím'),
]

class Tag(models.Model):
    _name = 'ngsc.competency.tag'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Thẻ'

    name = fields.Char(string=u'Tên thẻ', help=u'tên thẻ', required=True, tracking=True)
    code = fields.Char(string=u'Mã thẻ', help=u'mã thẻ', unique=True, readonly=True)
    active = fields.Boolean(string=u'Hoạt động', help=u'trạng thái hoạt động', default=True, tracking=True)
    color_code = fields.Integer(string=u'Mã màu', help=u'Mã màu hiển thị', tracking=False)
    color_name = fields.Selection(selection=COLOR_SELECTION, string=u'Màu thẻ', tracking=True)
    description = fields.Text(string=u'Mô tả', help=u'mô tả', tracking=True)
    skill_group_id = fields.Many2one(string=u'Nhóm kỹ năng', comodel_name='ngsc.competency.skill.group', required=True, tracking=True)
    active_display = fields.Char(string=u'Trạng thái', compute='_compute_active_display', store=True)

    @api.model
    def create(self, vals):
        res = super(Tag, self).create(vals)
        res.code = self.env['ir.sequence'].next_by_code('ngsc.competency.tag.code')
        return res

    @api.depends('active')
    def _compute_active_display(self):
        for record in self:
            record.active_display = STATUS_ACTIVE if record.active else STATUS_INACTIVE

    def name_get(self):
        result = []
        for rec in self:
            display_name = f"{rec.code or ''} - {rec.name or ''}"
            result.append((rec.id, display_name))
        return result

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        domain = ['|', ('code', operator, name), ('name', operator, name)]
        records = self.search(domain + args, limit=limit)
        records = records.sorted(key=lambda r: (r.code or '', r.name or ''))
        return records.name_get()

    @api.constrains('name', 'skill_group_id')
    def _check_unique_name_per_group(self):
        for record in self:
            if record.name and record.skill_group_id:
                duplicates = self.search([
                    ('name', '=', record.name),
                    ('skill_group_id', '=', record.skill_group_id.id),
                    ('id', '!=', record.id)
                ], limit=1)
                if duplicates:
                    raise ValidationError(
                        f"Tên thẻ '{record.name}' đã tồn tại trong nhóm kỹ năng '{record.skill_group_id.name}'."
                    )

    @api.onchange('color_code')
    def _sync_color_name(self):
        if self.color_code is not None:
            self.color_name = str(self.color_code)
