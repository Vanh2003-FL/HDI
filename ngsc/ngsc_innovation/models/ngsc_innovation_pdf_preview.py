from odoo import models, fields, api

class NgscInnovationPdfPreview(models.Model):
    _name = 'ngsc_innovation.pdf_preview'
    _description = 'NGSC Innovation PDF Preview'

    name = fields.Char(string='Tên tài liệu', required=True)
    pdf_file = fields.Binary(string='File PDF', attachment=True)
    pdf_filename = fields.Char(string='Tên file PDF')
    active = fields.Boolean(string='Đang sử dụng', default=True)

    @api.model
    def create(self, vals):
        # Khi tạo mới -> set active=True và tắt tất cả bản ghi khác
        vals['active'] = True
        record = super(NgscInnovationPdfPreview, self).create(vals)
        record._deactivate_others()
        return record

    def write(self, vals):
        res = super(NgscInnovationPdfPreview, self).write(vals)
        # Nếu bản ghi được set active=True thì tắt các bản ghi khác
        if 'active' in vals and vals['active']:
            self._deactivate_others()
        return res

    def _deactivate_others(self):
        # Tắt tất cả bản ghi khác (chỉ để lại bản ghi hiện tại active)
        self.search([
            ('id', '!=', self.id),
            ('active', '=', True)
        ]).write({'active': False})

