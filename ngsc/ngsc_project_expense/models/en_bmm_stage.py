from odoo import models, fields, api, _, exceptions
from odoo.exceptions import ValidationError


class BmmStage(models.Model):
    _name = "en.bmm.stage"
    _description = "BMM theo giai đoan dự án"

    project_id = fields.Many2one("project.project", string="Dự án", index=True)
    bmm_stage_id = fields.Many2one("en.stage.type", string="Giai đoạn", index=True)
    number_of_week = fields.Integer(string="Số tuần")
    date_start = fields.Date(string="Ngày bắt đầu")
    date_end = fields.Date(string="Ngày kết thúc")
    bmm = fields.Float(string="BMM")
    expense = fields.Monetary(string="Chi phí", currency_field="company_currency")
    company_currency = fields.Many2one("res.currency", string="Currency", compute="_compute_company_currency")

    def _compute_company_currency(self):
        for rec in self:
            rec.company_currency = self.env.company.currency_id.id

    @api.constrains("number_of_week", "expense", "bmm")
    def _check_number_of_week_expense(self):
        for rec in self:
            if rec.number_of_week <= 0:
                raise ValidationError("Số tuần phải lớn hơn 0")
            if rec.expense < 0:
                raise ValidationError("Chi phí không được nhỏ hơn 0")
            if rec.bmm < 0:
                raise ValidationError("BMM không được nhỏ hơn 0")

