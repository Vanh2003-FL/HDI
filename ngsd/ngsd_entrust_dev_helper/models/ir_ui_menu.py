from odoo import *


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'action' in vals and not 'name' in vals:
                to_action = vals.get('action').split(",")
                vals['name'] = self.env[to_action[0]].browse(int(to_action[1])).name
        return super().create(vals_list)
