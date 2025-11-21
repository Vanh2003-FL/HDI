from odoo import models, fields, api, _, exceptions
from odoo.exceptions import ValidationError


class ResourceExpense(models.Model):
    _name = "ngsc.resource.expense"
    _description = "BMM theo giai giai nguồn lực"

    resource_planning_id = fields.Many2one("en.resource.planning", string="Nguồn lực")
    project_id = fields.Many2one("project.project", string="Dự án")
    stage_id = fields.Many2one("en.stage.type", string="Giai đoạn")
    project_bmm = fields.Float(string="BMM dự án")
    planned_bmm = fields.Float(string="BMM kế hoạch")
    actual_bmm = fields.Float(string="BMM thực tế")
    project_expense = fields.Monetary(string="Chi phí dự án", currency_field="company_currency")
    planned_expense = fields.Monetary(string="Chi phí kế hoạch", currency_field="company_currency")
    actual_expense = fields.Monetary(string="Chi phí thực tế", currency_field="company_currency")
    company_currency = fields.Many2one("res.currency", string="Currency", compute="_compute_company_currency")

    def _compute_company_currency(self):
        for rec in self:
            rec.company_currency = self.env.company.currency_id.id

