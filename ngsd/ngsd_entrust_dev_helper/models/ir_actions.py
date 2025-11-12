
from odoo import *


class IrActionsActWindow(models.Model):
    _inherit = 'ir.actions.act_window'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'res_model' in vals and not 'name' in vals:
                vals['name'] = self.env[vals.get('res_model')]._description
        return super().create(vals_list)
