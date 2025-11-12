from odoo import models, api


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _notify_thread(self, message, msg_vals=False, notify_by_email=True, **kwargs):
        rdata = super()._notify_thread(message, msg_vals=msg_vals, notify_by_email=notify_by_email, **kwargs)
        inbox_rdata = []
        email_rdata = []
        for partner_data in rdata:
            if partner_data['notif'] == 'both':
                inbox_partner = partner_data.copy()
                email_partner = partner_data.copy()
                inbox_partner['notif'] = 'inbox'
                email_partner['notif'] = 'email'
                inbox_rdata.append(inbox_partner)
                email_rdata.append(email_partner)
        self._notify_record_by_inbox(message, inbox_rdata, msg_vals=msg_vals, **kwargs)
        self._notify_record_by_email(message, email_rdata, msg_vals=msg_vals, **kwargs)
        return rdata
