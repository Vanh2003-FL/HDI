from odoo import api, fields, models
from odoo.exceptions import ValidationError


class BMM(models.Model):
    _inherit = "en.bmm"

    expense = fields.Monetary(string="Chi phí", currency_field="company_currency")
    company_currency = fields.Many2one("res.currency", string="Currency", compute="_compute_company_currency")
    is_qa = fields.Boolean(compute='_compute_has_group_quality_assurance')

    def _compute_has_group_quality_assurance(self):
        has_group = self.env.user.has_group('ngsd_base.group_qal,ngsd_base.group_qam')
        for rec in self:
            rec.is_qa = True if has_group else False

    def _compute_company_currency(self):
        for lead in self:
            lead.company_currency = self.env.company.currency_id.id

    @api.onchange('expense')
    def _onchange_expense(self):
        for rec in self:
            if rec.expense < 0:
                raise ValidationError('Chi phí không được nhỏ hơn 0')
