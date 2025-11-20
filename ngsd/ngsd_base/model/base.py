from odoo import api, models, _, exceptions, fields, SUPERUSER_ID
from odoo.fields import Domain


class Base(models.AbstractModel):
  _inherit = "base"

  def _read(self, fields):
    if fields == ['user_ids'] and self._name == 'res.partner':
      self = self.sudo()
    return super(Base, self)._read(fields)

  def read(self, fields=None, load='_classic_read'):
    if fields == ['im_status'] or fields == [
      'commercial_partner_id'] or fields == ['display_name'] or fields == [
      'display_name', 'color']:
      self = self.sudo()
    return super(Base, self).read(fields=fields, load=load)


class MailThread(models.AbstractModel):
  _inherit = 'mail.thread'

  def _message_compute_author(self, author_id=None, email_from=None,
      raise_on_email=False):
    author_id, email_from = super(MailThread, self)._message_compute_author(
      author_id, email_from)
    mail_server = self.env["ir.mail_server"].sudo().search([], order='sequence',
                                                           limit=1)
    if mail_server:
      email_from = f""""Quan Tri Noi Bo" <{mail_server.smtp_user}>"""
    return author_id, email_from
