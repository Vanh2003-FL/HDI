from odoo import *


class IrRule(models.Model):
    _inherit = 'ir.rule'

    def _get_rules(self, model_name, mode='read'):
        res = super()._get_rules(model_name=model_name, mode=mode)
        if model_name == 'project.project':
            if self._context.get('view_internal_project'):
                res |= self.env.ref('ngsd_base.access_user_to_internal_project')
        return res

    def _compute_domain_keys(self):
        res = super()._compute_domain_keys()
        return res + ['view_internal_project']
