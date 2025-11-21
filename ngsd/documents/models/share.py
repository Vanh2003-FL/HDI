# -*- coding: utf-8 -*-

from ast import literal_eval
from odoo import models, fields, api, exceptions
from odoo.tools.translate import _
from odoo.tools import consteq
import uuid


class DocumentShare(models.Model):
    _name = 'documents.share'
    _inherit = ['mail.thread', 'mail.alias.mixin']
    _description = 'Documents Share'

    folder_id = fields.Many2one('documents.folder', string="Workspace", required=True, ondelete='cascade')
    name = fields.Char(string="Name")

    access_token = fields.Char(required=True, default=lambda x: str(uuid.uuid4()), groups="documents.group_documents_user")
    full_url = fields.Char(string="URL", compute='_compute_full_url')
    date_deadline = fields.Date(string="Valid Until")
    state = fields.Selection([
        ('live', "Live"),
        ('expired', "Expired"),
    ], default='live', compute='_compute_state', string="Status")
    can_upload = fields.Boolean(compute='_compute_can_upload')

    type = fields.Selection([
        ('ids', "Document list"),
        ('domain', "Domain"),
    ], default='ids', string="Share type")

    document_ids = fields.Many2many('documents.document', string='Shared Documents')
    domain = fields.Char()

    action = fields.Selection([
        ('download', "Download"),
        ('downloadupload', "Download and Upload"),
    ], default='download', string="Allows to")

    tag_ids = fields.Many2many('documents.tag', string="Shared Tags")
    partner_id = fields.Many2one('res.partner', string="Contact")
    owner_id = fields.Many2one('res.users', string="Document Owner")
    email_drop = fields.Boolean(string='Upload by Email')

    activity_option = fields.Boolean(string='Create a new activity')
    activity_type_id = fields.Many2one('mail.activity.type', string="Activity type")
    activity_summary = fields.Char('Summary')
    activity_date_deadline_range = fields.Integer(string='Due Date In')
    activity_date_deadline_range_type = fields.Selection([
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
    ], string='Due type', default='days')
    activity_note = fields.Html(string="Note")
    activity_user_id = fields.Many2one('res.users', string='Responsible')

    _sql_constraints = [
        ('share_unique', 'unique (access_token)', "This access token already exists"),
    ]

    def name_get(self):
        return [(rec.id, rec.name or "unnamed link") for rec in self]

    def _get_documents(self, document_ids=None):
        self.ensure_one()
        limited_self = self.with_user(self.create_uid)
        Documents = limited_self.env['documents.document']

        search_ids = set()
        domains = [[('folder_id', '=', self.folder_id.id)]]

        if document_ids is not None:
            if not document_ids:
                return Documents
            search_ids = set(document_ids)

        if self.type == 'domain':
            record_domain = []
            if self.domain:
                record_domain = literal_eval(self.domain)
            domains.append(record_domain)
            if self.action == 'download':
                domains.append([('type', '!=', 'empty')])
        else:
            share_ids = limited_self.document_ids.ids
            search_ids = search_ids.intersection(share_ids) if search_ids else set(share_ids)

        if search_ids or self.type != 'domain':
            domains.append([('id', 'in', list(search_ids))])

        # Domain AND = nối list
        search_domain = []
        for d in domains:
            search_domain += d

        return Documents.search(search_domain)

    def _get_writable_documents(self, documents):
        self.ensure_one()
        try:
            documents.with_user(self.create_uid).check_access_rights('write')
        except exceptions.AccessError:
            return False
        return documents.with_user(self.create_uid)._filter_access_rules('write')

    def _check_token(self, access_token):
        if not access_token:
            return False
        try:
            return consteq(access_token, self.access_token)
        except:
            return False

    def _get_documents_and_check_access(self, access_token, document_ids=None, operation='write'):
        self.ensure_one()
        if not self._check_token(access_token):
            return False
        if self.state == 'expired':
            return False
        documents = self._get_documents(document_ids)
        return self._get_writable_documents(documents) if operation == 'write' else documents

    def _compute_can_upload(self):
        for record in self:
            folder = record.folder_id
            folder_has_groups = folder.group_ids.ids or folder.read_group_ids.ids
            in_write_group = set(folder.group_ids.ids) & set(record.create_uid.groups_id.ids)
            record.can_upload = in_write_group or not folder_has_groups

    def _compute_state(self):
        for record in self:
            record.state = 'live'
            if record.date_deadline:
                today = fields.Date.today()
                if record.date_deadline <= today:
                    record.state = 'expired'

    @api.onchange('access_token')
    def _compute_full_url(self):
        for record in self:
            record.full_url = "%s/document/share/%s/%s" % (record.get_base_url(), record.id, record.access_token)

    def _alias_get_creation_values(self):
        values = super()._alias_get_creation_values()
        values['alias_model_id'] = self.env['ir.model']._get('documents.document').id
        if self.id:
            defaults = literal_eval(self.alias_defaults or "{}")
            defaults.update({
                'tag_ids': [(6, 0, self.tag_ids.ids)],
                'folder_id': self.folder_id.id,
                'partner_id': self.partner_id.id,
                'create_share_id': self.id,
            })
            values['alias_defaults'] = defaults
        return values

    def _get_share_popup(self, context, vals):
        view_id = self.env.ref('documents.share_view_form_popup').id
        return {
            'context': context,
            'res_model': 'documents.share',
            'target': 'new',
            'name': _('Share selected records') if vals.get('type') == 'ids' else _('Share domain'),
            'res_id': self.id if self else False,
            'type': 'ir.actions.act_window',
            'views': [[view_id, 'form']],
        }

    def send_share_by_mail(self, template_xmlid):
        self.ensure_one()
        template = self.env.ref(template_xmlid, raise_if_not_found=False)
        if template:
            template.send_mail(self.id)

    @api.model
    def create(self, vals):
        if not vals.get('owner_id'):
            vals['owner_id'] = self.env.uid
        return super().create(vals)

    @api.model
    def open_share_popup(self, vals):
        new_context = dict(self.env.context)
        new_context.update({
            'default_owner_id': self.env.uid,
            'default_folder_id': vals.get('folder_id'),
            'default_tag_ids': vals.get('tag_ids'),
            'default_type': vals.get('type', 'domain'),
            'default_domain': vals.get('domain') if vals.get('type', 'domain') == 'domain' else False,
            'default_document_ids': vals.get('document_ids', False),
        })
        return self._get_share_popup(new_context, vals)

    def action_delete_shares(self):
        self.unlink()

    def action_generate_url(self):
        return self._get_share_popup(self.env.context, {'type': self.type})
