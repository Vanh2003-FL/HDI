from odoo import models, fields, api, _, exceptions
from odoo.exceptions import ValidationError, UserError, AccessError



class OsExpense(models.Model):
    _name = "os.expense"
    _description = "Chi phí Outsource"

    employee_id = fields.Many2one("hr.employee", string="Nhân sự")
    date_start = fields.Date(string="Ngày bắt đầu", required=True)
    date_end = fields.Date(string="Ngày kết thúc", required=True)
    expense = fields.Monetary(string="Chi phí", currency_field="company_currency")
    company_currency = fields.Many2one("res.currency", string="Currency", compute="_compute_company_currency")

    def _compute_company_currency(self):
        for rec in self:
            rec.company_currency = self.env.company.currency_id.id

    @api.constrains('expense')
    def _constrains_expense(self):
        for rec in self:
            if rec.expense < 0:
                raise ValidationError('Chi phí phải là số dương')

    @api.constrains('date_start', 'date_end')
    def _constrains_date(self):
        for rec in self:
            if rec.date_end < rec.date_start:
                raise UserError('Ngày kết thúc phải lớn hơn ngày bắt đầu.')
            count_date_start = self.search_count(
                [('id', '!=', rec.id), ('date_start', '<=', rec.date_start), ('date_end', '>=', rec.date_start),
                 ('employee_id', '=', rec.employee_id.id)])
            count_date_end = self.search_count(
                [('id', '!=', rec.id), ('date_start', '<=', rec.date_end), ('date_end', '>=', rec.date_end),
                 ('employee_id', '=', rec.employee_id.id)])
            if count_date_start or count_date_end:
                raise UserError(
                    'Ngày bắt đầu, kết thúc không được trùng với quãng thời gian của bản ghi chi phí Outsource khác.')