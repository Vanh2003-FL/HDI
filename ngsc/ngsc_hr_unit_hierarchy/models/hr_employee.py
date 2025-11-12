# -*- coding: utf-8 -*-
from odoo import models, fields, api
from ..utils.query import *


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    en_department_id = fields.Many2one("en.department", string="Phòng")
    unit_id = fields.Many2one("ngsc.unit.hierarchy", string="Phân cấp phòng ban")

    def init(self):
        self.env.cr.execute(QUERY_SYNC_UNIT_HIERARCHY)

    def write(self, values):
        res = super().write(values)
        if any(key in values for key in ['en_department_id', 'department_id', 'en_block_id']):
            self._update_unit_hierarchy()
        return res

    def _update_unit_hierarchy(self):
        self.flush()
        for rec in self:
            self.env.cr.execute(QUERY_UPDATE_UNIT_HIERARCHY % rec.id)