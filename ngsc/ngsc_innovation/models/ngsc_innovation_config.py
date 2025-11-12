from odoo import models, fields, api

class NGSCInnovationConfig(models.Model):
    _name = 'ngsc.innovation.config'
    _description = 'NGSC - Cấu hình sáng kiến'

    name = fields.Char(string='Tên cấu hình', required=True)
    type = fields.Selection([
        ('field', 'Phân loại theo lĩnh vực'),
        ('impact', 'Phân loại theo tác động'),
        ('status', 'Tình trạng hiện tại'),
    ], string='Loại cấu hình', required=True, default='field')
    status = fields.Boolean(string='Kích hoạt', default=True)