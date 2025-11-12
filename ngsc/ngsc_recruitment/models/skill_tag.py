from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
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


class SkillTag(models.Model):
    _name = 'ngsc.recruitment.skill.tag'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Thẻ kỹ năng'

    name = fields.Char(string=u'Tên thẻ', help=u'tên thẻ', required=True, tracking=True)
    code = fields.Char(string=u'Mã thẻ', help=u'mã thẻ', unique=True, readonly=True)
    active = fields.Boolean(string=u'Hoạt động', help=u'trạng thái hoạt động', default=True, tracking=True)
    color_code = fields.Integer(string=u'Mã màu', help=u'Mã màu hiển thị', tracking=False)
    color_name = fields.Selection(selection=COLOR_SELECTION, string=u'Màu thẻ', tracking=True)
    description = fields.Text(string=u'Mô tả', help=u'mô tả', tracking=True)
    active_display = fields.Char(string=u'Trạng thái', compute='_compute_active_display', store=True)

    @api.model
    def create(self, vals):
        res = super(SkillTag, self).create(vals)
        res.code = self.env['ir.sequence'].next_by_code('ngsc.recruitment.skill.tag.code')
        return res

    @api.depends('active')
    def _compute_active_display(self):
        for record in self:
            record.active_display = STATUS_ACTIVE if record.active else STATUS_INACTIVE

    @api.onchange('color_code')
    def _sync_color_name(self):
        if self.color_code is not None:
            self.color_name = str(self.color_code)

    @api.constrains('name')
    def _check_unique_name(self):
        for record in self:
            # Tìm các record khác có cùng tên, ngoại trừ record hiện tại
            duplicate = self.search([
                ('name', '=', record.name),
                ('id', '!=', record.id)
            ], limit=1)
            if duplicate:
                raise ValidationError(
                    f"Thẻ '{record.name}' đã tồn tại. Vui lòng chọn một tên khác."
                )

    def unlink(self):
        for skill_tag in self:
            personnel_records = self.env['ngsc.recruitment.source.personnel'].search([
                ('skill_tag', 'in', [skill_tag.id])
            ])
            if personnel_records:
                raise UserError(
                    f"Không thể xóa thẻ kỹ năng '{skill_tag.name}' vì nó đang được sử dụng trong các hồ sơ nguồn: {', '.join(personnel_records.mapped('name'))}"
                )
        return super(SkillTag, self).unlink()
