from datetime import datetime
import datetime

from odoo import models, fields, api, _, exceptions
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import ValidationError, UserError


class ResUsers(models.Model):
    _inherit = 'res.users'

    role_ids = fields.Many2many('entrust.role', 'res_users_roles_rel', 'uid', 'rid', string='Vai trò')
    disallowed_menu_ids = fields.Many2many('ir.ui.menu', string='Not-allowed Menu')

    @api.onchange('role_ids')
    def _onchange_role(self):
        if self.role_ids:
            self.disallowed_menu_ids = self.role_ids.mapped('disallowed_menu_ids')
        else:
            self.role_ids = False

    @api.model_create_multi
    def create(self, vals_list):
        records = super(ResUsers, self).create(vals_list)
        for rec in records:
            rec.reload_groups_id()
        return records

    def write(self, vals):
        res = super().write(vals)
        if 'role_ids' in vals:
            self.reload_groups_id()
        if 'disallowed_menu_ids' in vals:
            self.env['ir.ui.menu'].clear_caches()
        return res

    def reload_groups_id(self):
        for rec in self:
            if rec.role_ids:
                rec.with_context(mail_channel_nosubscribe=True).write({'disallowed_menu_ids': [(5, 0, 0)] + [(4, menu.id) for menu in rec.mapped('role_ids.disallowed_menu_ids')], 'groups_id': [(5, 0, 0)] + [(4, group.id) for group in rec.mapped('role_ids.groups_id')]})
