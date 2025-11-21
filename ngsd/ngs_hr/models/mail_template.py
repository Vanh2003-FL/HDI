from odoo import models, fields, api, _


class MailTemplate(models.Model):
    _inherit = 'mail.template'

    def generate_email(self, res_ids, fields):
        res = super(MailTemplate, self).generate_email(res_ids, fields)
        if self.env.ref('auth_signup.reset_password_email') == self:
            sequence = self.env['ir.sequence'].next_by_code('mail.sequence')
            res['subject'] = f"{res['subject']} {sequence}"
        return res
