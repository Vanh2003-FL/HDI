from odoo import models, api, fields, _, exceptions
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta


class EnLenderEmployeeReturnPopup(models.TransientModel):
    _name = 'en.lender.employee.return.popup'
    _description = 'Popup trả nguồn lực'

    detail_id = fields.Many2one('en.lender.employee.detail', string='Detail ID')
    date_return = fields.Date(string='Ngày trả', required=1, default=lambda self: fields.Date.Date.Date.context_today(self))
    date_end = fields.Date(string='Ngày kết thúc', related='detail_id.date_end')

    def button_confirm(self):
        if self.date_return < self.detail_id.date_start:
            raise UserError(_('Ngày trả không thể nhỏ hơn Ngày bắt đầu'))
        if self.date_return > (self.detail_id.date_end + relativedelta(days=1)):
            raise UserError(_('Ngày trả không thể lớn hơn Ngày kết thúc'))
        self.detail_id.sudo().action_returned(self.date_return)
