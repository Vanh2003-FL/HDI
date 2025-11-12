from odoo import models, api, fields
from odoo.exceptions import UserError


class MessagePopupConfirm(models.TransientModel):
    _name = 'message.popup.confirm'

    message = fields.Text('Thông báo', required=True, readonly=True)
    master_id = fields.Char('Master ID')
    func = fields.Char('Loại')

    def button_confirm(self):
        model, res_id = self.get_master_id()
        getattr(self.env[model].browse(res_id), self.func)()

    def get_master_id(self):
        if not self.master_id:
            raise UserError('Không tìm thấy Master ID!')
        model, id = self.master_id.split(',')
        if id == 'False':
            id = False
        return model, int(id)