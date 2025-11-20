from odoo import models


class IrModel(models.Model):
    _inherit = 'ir.model'

    def name_get(self):
        return [(rec.id, f'{rec.name} ({rec.model})') for rec in self]
