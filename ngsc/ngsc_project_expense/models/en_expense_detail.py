from odoo import models, fields, api, _, exceptions
from odoo.exceptions import ValidationError, UserError, AccessError


class ExpenseDetail(models.Model):
    _name = "en.expense.detail"
    _rec_name = "level_id"
    _description = "Chi phí cấp bậc"

    level_id = fields.Many2one("en.name.level", string="Cấp bậc")
    date_start = fields.Date("Thời gian bắt đầu")
    date_end = fields.Date("Thời gian kết thúc")
    expense = fields.Monetary(string="Chi phí", currency_field="company_currency", tracking=True)
    company_currency = fields.Many2one("res.currency", string="Currency", compute="_compute_company_currency")
    department_ids = fields.Many2many("hr.department", "expense_detail_department_rel", "expense_detail_id",
                                      "department_id", string="Trung tâm")

    def _compute_company_currency(self):
        for lead in self:
            lead.company_currency = self.env.company.currency_id.id

    @api.onchange('expense')
    def _onchange_expense(self):
        for rec in self:
            if rec.expense < 0:
                raise ValidationError('Chi phí không được nhỏ hơn 0')

    @api.constrains('date_start', 'date_end')
    def _constrains_date(self):
        for rec in self:
            expenses = self.search([('id', '!=', rec.id), ('level_id', '=', rec.level_id.id)])
            if rec.date_end and rec.date_start and rec.date_end < rec.date_start:
                raise ValidationError('Thời gian kết thúc không được lớn hơn thời gian bắt đầu')
            for e in expenses:
                if rec.date_start and e.date_start <= rec.date_start <= e.date_end and rec.department_ids & e.department_ids:
                    raise ValidationError('Trung tâm đã có chi phí trong quãng thời gian này')
                if rec.date_end and e.date_start <= rec.date_end <= e.date_end and rec.department_ids & e.department_ids:
                    raise ValidationError('Trung tâm đã có chi phí trong quãng thời gian này')
