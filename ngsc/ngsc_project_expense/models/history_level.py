from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _, exceptions
from odoo.exceptions import ValidationError, UserError, AccessError


class HistoryLevel(models.Model):
    _name = "history.level"
    _description = 'Lịch sử cấp bậc'
    _order = 'date_start'

    employee_id = fields.Many2one("hr.employee", string="Nhân sự")
    date_start = fields.Date(string="Ngày bắt đầu", required=True)
    date_end = fields.Date(string="Ngày kết thúc", compute="_compute_date_end", store=True)
    level_id = fields.Many2one('en.name.level', string="Cấp bậc", required=True)

    @api.constrains('date_start')
    def _constrains_date_start(self):
        for rec in self:
            count_history_level = self.search_count(
                [('id', '!=', rec.id), ('date_start', '=', rec.date_start), ('employee_id', '=', rec.employee_id.id)])
            if count_history_level:
                raise UserError('Ngày bắt đầu không được trùng với ngày bắt đầu của bản ghi lịch sử cấp bậc khác.')

    @api.depends('employee_id.history_level_ids.date_start')
    def _compute_date_end(self):
        for rec in self:
            if rec.date_start:
                next_record = self.search(
                    [('date_start', '>', rec.date_start), ('employee_id', '=', rec.employee_id.id)], limit=1)
                rec.date_end = next_record.date_start - relativedelta(days=1) if next_record.date_start else False
            else:
                rec.date_end = False
