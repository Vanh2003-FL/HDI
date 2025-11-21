# -*- coding: utf-8 -*-
# author     :guoyihot@outlook.com
# date       ：
# description:

from odoo import models, fields, api, _, exceptions
from odoo.exceptions import UserError
import operator
import re


class BaseImport(models.TransientModel):
    _inherit = "base_import.import"

    def execute_import(self, fields, columns, options, dryrun=False):
        res = super(BaseImport, self.with_context(dryrun=dryrun, import_order_line=options.get('import_order_line'), relation_id=options.get('order_id'))).execute_import(fields, columns, options, dryrun)
        return res

    @api.model
    def _convert_import_data(self, fields, options):
        data, fields = super(BaseImport, self)._convert_import_data(fields, options)
        if self._context.get('import_order_line'):
            import_field = options.get('import_field')
            order_id = options.get('order_id')
            if import_field and order_id:
                idx_row_in_model = 0
                for idx, f in enumerate(fields):
                    if '/' not in f:
                        idx_row_in_model = idx
                        break
                fields.insert(idx_row_in_model, import_field)
                for row in data:
                    dta = ''
                    if row[idx_row_in_model]:
                        dta = order_id
                    row.insert(idx_row_in_model, dta)
        # data = [[cell.strip() if type(cell) == str else cell for cell in row] for row in data]
        return data, fields
