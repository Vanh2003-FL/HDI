from odoo import *


class EnFiscalYear(models.Model):
    _name = 'en.fiscal.year'
    _description = 'Năm tài chính'

    name = fields.Char('Tên', required=1)
    start_date = fields.Date('Thời gian bắt đầu', required=1)
    end_date = fields.Date('Thời gian kết thúc', required=1)
