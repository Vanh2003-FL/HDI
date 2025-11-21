# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from ..utils.query import *


class EnNameBlock(models.Model):
    _inherit = "en.name.block"

    @api.model
    def create(self, values):
        res = super().create(values)
        res._create_unit_hierarchy()
        return res

    def write(self, values):
        res = super().write(values)
        if any(key in values for key in ['name', 'active', 'area_id']):
            self._sync_unit_hierarchy()
        return res

    def unlink(self):
        for rec in self:
            rec._delete_unit_hierarchy()
        return super().unlink()

    def _sync_unit_hierarchy(self):
        self.flush()
        self.env.cr.execute(QUERY_SYNC_UNIT_HIERARCHY)

    def _create_unit_hierarchy(self):
        vals = {
            "name": self.name,
            "unit_type": 'block',
            "block_id": self.id,
        }
        self.env["ngsc.unit.hierarchy"].sudo().create(vals)

    def _delete_unit_hierarchy(self):
        record = self.env["ngsc.unit.hierarchy"].sudo().search([('block_id', '=', self.id)], limit=1)
        child_records = self.env["ngsc.unit.hierarchy"].sudo().search([('parent_id', 'child_of', record.id)])
        child_records.unlink()