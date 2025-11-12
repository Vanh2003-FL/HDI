import math
from datetime import datetime, time
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResourceDetail(models.Model):
    _inherit = "en.resource.detail"

    def _auto_init(self):
        self._cr.execute("""alter table en_resource_detail add column if not exists expense numeric;""")
        return super()._auto_init()

    expense = fields.Monetary(string="Chi phí", currency_field="company_currency", compute="_compute_expense", store=True)
    company_currency = fields.Many2one("res.currency", string="Currency", compute="_compute_company_currency")

    @api.depends("employee_id", "employee_id.history_level_ids", "workload", "employee_id.os_expense_ids")
    def _compute_expense(self):
        for rec in self:
            if not rec.employee_id or not rec.date_start or not rec.date_end:
                rec.expense = 0
                continue
            date_from = min([rec.date_start, rec.date_end])
            date_to = max([rec.date_start, rec.date_end])
            datetime_from = datetime.combine(date_from, time.min)
            datetime_to = datetime.combine(date_to, time.max)
            employee = rec.employee_id
            expense = self.env['en.technical.model'].convert_daterange_to_expense(employee, datetime_from, datetime_to,
                                                                                  exclude_tech_type=['off', 'holiday'])
            rec.expense = math.ceil(expense * rec.workload)

    def _compute_company_currency(self):
        for lead in self:
            lead.company_currency = self.env.company.currency_id.id

    @api.model
    def _recompute_expense(self):
        batch_size = 100
        all_ids = self.ids
        for start in range(0, len(all_ids), batch_size):
            end = start + batch_size
            batch_ids = all_ids[start:end]
            batch = self.browse(batch_ids)
            batch.with_delay()._compute_expense()