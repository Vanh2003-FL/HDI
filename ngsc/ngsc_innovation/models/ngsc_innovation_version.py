from odoo import models, fields, api
from datetime import date
from odoo.exceptions import ValidationError


class InnovationVersion(models.Model):
    _name = 'ngsc.innovation.version'
    _description = 'Phiên bản sáng kiến'
    _order = 'start_date desc'

    ver_no = fields.Char(string='Số phiên bản', required=True)
    start_date = fields.Date(
        string='Ngày bắt đầu',
        required=True,
        default=lambda self: fields.Date.today()
    )
    end_date = fields.Date(string='Ngày kết thúc')
    status = fields.Boolean(string='Áp dụng', default=True)
    criteria_ids = fields.One2many(
        'ngsc.scoring.criteria',
        'version_id',
        string='Các tiêu chí chấm điểm'
    )

    @api.model
    def create(self, vals):
        today = date.today()

        # Ngày bắt đầu mặc định = hôm nay nếu chưa set
        if not vals.get('start_date'):
            vals['start_date'] = today

        # Nếu status được bật thì tắt tất cả version khác
        if vals.get('status', False):
            self.search([('status', '=', True)]).write({'status': False})

        # Lấy version gần nhất trước ngày bắt đầu mới
        # Lấy version gần nhất (theo ID) trước khi tạo mới
        previous_version = self.search([], order="id desc", limit=1)

        # Tạo version mới
        new_record = super(InnovationVersion, self).create(vals)

        if previous_version:
            # Nếu version cũ chưa có ngày kết thúc => set hôm nay
            if not previous_version.end_date:
                previous_version.end_date = new_record.start_date

            # Clone tiêu chí từ version cũ sang version mới
            for criteria in previous_version.criteria_ids:
                criteria.copy({
                    'version_id': new_record.id
                })

        return new_record

    def write(self, vals):
        # Khi update mà bật status => tắt version khác
        if vals.get('status', False):
            self.search([('id', '!=', self.id), ('status', '=', True)]).write({'status': False})
        return super(InnovationVersion, self).write(vals)
    @api.onchange('end_date')
    def _onchange_end_date(self):
        """Kiểm tra end_date phải sau hoặc bằng start_date khi người dùng nhập end_date"""
        for record in self:
            if record.end_date and record.start_date and record.end_date < record.start_date:
                raise ValidationError("Ngày kết thúc phải sau hoặc bằng ngày bắt đầu.")