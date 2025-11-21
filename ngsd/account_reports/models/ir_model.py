# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class IrModel(models.Model):
    _inherit = 'ir.model'

    def name_get(self):
        result = []
        if self._context.get('append_type_to_tax_name'):
            for record in self:
                name = record.name
                result += [(record.id, name)]
        result = super().name_get()
        return result
