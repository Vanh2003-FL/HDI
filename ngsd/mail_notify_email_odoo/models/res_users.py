from odoo import models, fields, api, _


class Users(models.Model):
    _inherit = 'res.users'

    notification_type = fields.Selection(selection_add=[
        ('both', 'Xử lý bằng cả Email và hệ thống Odoo')
    ], ondelete={'both': 'set default'}
    )

    @api.model
    def default_get(self, fields):
        vals = super(Users, self).default_get(fields)
        if 'notification_type' in vals:
            vals['notification_type'] = 'both'
        return vals
