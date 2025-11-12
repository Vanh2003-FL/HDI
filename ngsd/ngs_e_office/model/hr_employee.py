# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import calendar
from dateutil.relativedelta import relativedelta
from math import copysign

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero, float_round


class Employee(models.Model):
    _inherit = 'hr.employee'

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        if self._context.get('view_all_employee') or self._context.get('ctx_view_employee'):
            self = self.sudo()
            business_plan_id = self._context.get('business_plan', False)
            if business_plan_id:
                business_plan = self.env['business.plan'].sudo().browse(business_plan_id)
                args += [['id', 'in', business_plan.partner_ids.mapped('employee_id.id')]]
        return super(Employee, self)._name_search(name=name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid)

    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        args = args or []
        if self._context.get('ctx_view_employee'):
            self = self.sudo()
            business_plan_id = self._context.get('business_plan', False)
            if business_plan_id:
                business_plan = self.env['business.plan'].sudo().browse(business_plan_id)
                args += [['id', 'in', business_plan.partner_ids.mapped('employee_id.id')]]
        return super(Employee, self)._search(args, offset=offset, limit=limit, order=order, count=count, access_rights_uid=access_rights_uid)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        if self._context.get('ctx_view_employee'):
            self = self.sudo()
            business_plan_id = self._context.get('business_plan', False)
            if business_plan_id:
                business_plan = self.env['business.plan'].sudo().browse(business_plan_id)
                domain += [['id', 'in', business_plan.partner_ids.mapped('employee_id.id')]]
        return super(Employee, self).search_read(domain, fields, offset, limit, order)

    def name_get(self):
        if self._context.get('ctx_view_employee'):
            self = self.sudo()
        return super(Employee, self.sudo()).name_get()