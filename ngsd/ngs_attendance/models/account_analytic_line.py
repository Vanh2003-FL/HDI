from odoo import models, fields, api, _, exceptions
import logging

_logger = logging.getLogger(__name__)
from odoo.exceptions import UserError


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    explanation_id = fields.Many2one('hr.attendance.explanation', string="Giải trình chấm công", readonly=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        res = super(AccountAnalyticLine, self).create(vals_list)
        if self._context.get('timesheet_from_explanation'):
            for rec in res:
                if rec.explanation_id.state == 'new':
                    rec.explanation_id.apply_approver()
                if rec.project_id and not self.env['en.resource.detail'].search_count([('employee_id', '=', rec.employee_id.id), ('date_start', '<=', rec.date),('date_end', '>=', rec.date), ('order_id', '=', rec.project_id.en_resource_id.id)]):
                    raise UserError('Timesheet bạn vừa khai báo nằm ngoài thời gian làm việc của bạn trong Kế hoạch nguồn lực. Vui lòng liên hệ PM để được xử lý.')
        return res

    def button_explanation_confirm(self):
        return
