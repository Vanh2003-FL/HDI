# Copyright 2018-2019 Alexandre Díaz
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, _


class ResUsers(models.Model):
    _inherit = "res.users"

    chatter_position = fields.Selection(
        string='Vị trí chatter',
        selection=[("normal", "Ngang"), ("sided", "Dọc")],
        default="sided",
    )

    """Override to add access rights.
    Access rights are disabled by default, but allowed on some specific
    fields defined in self.SELF_{READ/WRITE}ABLE_FIELDS.
    """

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ["chatter_position"]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ["chatter_position"]
