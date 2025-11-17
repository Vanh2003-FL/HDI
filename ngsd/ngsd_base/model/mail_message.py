from odoo import fields, models, api

from odoo.osv import expression


class MailMessage(models.Model):
  _inherit = 'mail.message'

  @api.model
  def _message_fetch(self, domain, max_id=None, min_id=None, limit=30):
    """ Get a limited amount of formatted messages with provided domain.
            :param domain: the domain to filter messages;
            :param min_id: messages must be more recent than this id
            :param max_id: message must be less recent than this id
            :param limit: the maximum amount of messages to get;
            :returns list(dict).
        """
    if max_id:
      domain = expression.AND([domain, [('id', '<', max_id)]])
    if min_id:
      domain = expression.AND([domain, [('id', '>', min_id)]])
    messages = self.search(domain, limit=limit)
    new_messages = messages
    for message in messages:
      if message.model and message.res_id and not self.env[
        message.model].browse(message.res_id).exists():
        new_messages -= message
    return new_messages.message_format()


class MailMail(models.Model):
  _inherit = 'mail.mail'

  @api.model_create_multi
  def create(self, vals_list):
    # Handle both single record and batch creation
    if not isinstance(vals_list, list):
      vals_list = [vals_list]

    email_cc = self._context.get('hr_leave_email_cc', False)
    if email_cc:
      for values in vals_list:
        values['email_cc'] = email_cc
    return super().create(vals_list)
