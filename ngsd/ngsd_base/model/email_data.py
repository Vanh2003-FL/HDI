from odoo import api, fields, models, Command, _
from odoo.exceptions import UserError, ValidationError
import json


class EmailData(models.Model):
    _name = 'email.data'
    _description = 'Email Data'

    lead_id = fields.Many2one('crm.lead', string='Cơ hội')
    tmp = fields.Char('Template')
    email_to = fields.Char('Người nhận')
    ctx = fields.Text('CTX')
    id_mess = fields.Char('ID mess trả về')
    state = fields.Selection(selection=[('new', 'New'), ('sent', 'Sent'), ('cancel', 'Cancel')], string='Trạng thái', default='new')

    def _cron_send_mail(self):
        to_sends = self.search([('state', '=', 'new')])
        for to_send in to_sends:
            tmp = to_send.tmp
            email_to = to_send.email_to
            ctx = json.loads(to_send.ctx)
            id_mess = to_send.send_mail(tmp, email_to, ctx)
            if id_mess:
                to_send.write({'state': 'sent', 'id_mess': id_mess})
            else:
                to_send.write({'state': 'cancel'})

    def send_mail(self, tmp, email_to, ctx):
        if not tmp:
            return False
        template = self.env.ref(tmp, raise_if_not_found=False)
        if not template:
            return False
        record = False
        if self.lead_id:
            record = self.lead_id
        if record:
            id_mess = template.with_context(**ctx).send_mail(record.id, email_values={'email_to': email_to, 'email_from': ''}, notif_layout='', force_send=True)
            return id_mess
        return False
