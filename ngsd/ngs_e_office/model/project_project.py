# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import calendar
from dateutil.relativedelta import relativedelta
from math import copysign

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero, float_round


class Project(models.Model):
    _inherit = 'project.project'

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        if self._context.get('view_all_project') and self.env.user.has_group('ngsd_base.group_hcns'):
            self = self.sudo()
        return super(Project, self)._name_search(name=name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid)
