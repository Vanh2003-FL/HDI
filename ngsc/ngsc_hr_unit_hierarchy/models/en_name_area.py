# -*- coding: utf-8 -*-
from odoo import models, fields, api
from ..utils.query import *


class EnNameArea(models.Model):
    _inherit = "en.name.area"

    # @api.model
    # def create(self, values):
    #     res = super().create(values)
    #     res._sync_unit_hierarchy()
    #     return res
    #
    # def write(self, values):
    #     res = super().write(values)
    #     if any(key in values for key in ['name']):
    #         self._sync_unit_hierarchy()
    #     return res
    #
    # def unlink(self):
    #     self._sync_unit_hierarchy()
    #     return super().unlink()
    #
    # def _sync_unit_hierarchy(self):
    #     self.env.cr.execute(QUERY_SYNC_UNIT_HIERARCHY)
