from odoo import models, fields, api, _


class NameLevel(models.Model):
    _name = "en.name.level"
    _description = "Cấp bậc"

    sequence = fields.Integer("Vị trí sơ đồ", default=1)
    name = fields.Char(string="Cấp bậc")
    expense_ids = fields.One2many("en.expense.detail", "level_id", string="Chi phí")

    def write(self, values):
        res = super().write(values)
        if 'expense_ids' in values:
            for r in self:
                r.with_delay()._compute_data()
        return res

    def _compute_data(self):
        history_level_ids = self.env["history.level"].sudo().search([("level_id", "in", self.ids)])
        employee_ids = history_level_ids.mapped("employee_id.id")
        technical_model_ids = self.env["en.technical.model"].sudo().search([("employee_id", "in", employee_ids)])
        technical_model_ids._recompute_expense()
        resources = self.env["en.resource.detail"].search([("employee_id", "in", employee_ids),
                                                           ("date_start", "!=", False),
                                                           ("date_end", "!=", False)])
        resources._recompute_expense()
        plans = resources.mapped("order_id")
        for r in plans:
            r._update_resource_planing_expense()
