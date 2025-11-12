from odoo import models, api


class IrUiView(models.Model):
    _inherit = 'ir.ui.view'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'inherit_id' in vals and 'model' not in vals:
                vals['model'] = self.browse(vals.get('inherit_id')).model
            if 'model' in vals and 'name' not in vals:
                vals['name'] = self.env[vals.get('model')]._description
        return super().create(vals_list)
