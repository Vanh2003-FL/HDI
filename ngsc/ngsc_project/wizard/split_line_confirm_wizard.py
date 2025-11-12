from odoo import models, fields, api


class SplitLineConfirmWizard(models.TransientModel):
    _name = 'split.line.confirm.wizard'
    _description = 'Xác nhận tách dòng nguồn'

    def default_split_type(self):
        today = fields.Date.Date.context_today(self)
        five_day_of_month = today.replace(day=5)
        if today > five_day_of_month:
            return 'today'
        else:
            return 'first_day_of_month'

    def default_after_five_day_of_month(self):
        today = fields.Date.Date.context_today(self)
        five_day_of_month = today.replace(day=5)
        if today > five_day_of_month:
            return True
        else:
            return False

    detail_id = fields.Many2one('en.resource.detail', string='Dòng chi tiết', required=True)
    split_type = fields.Selection(string="Tách nguồn lực từ", required=True,
                                  selection=[('first_day_of_month', 'Đầu tháng hiện tại'),
                                             ('today', 'Ngày hiện tại')], default=default_split_type)
    is_after_five_day_of_month = fields.Boolean(string="Đã qua ngày 5 của tháng",
                                                default=default_after_five_day_of_month)

    def action_confirm_split_resource(self):
        if self.split_type == 'first_day_of_month':
            return self.action_confirm_split_first_month()
        else:
            return self.action_confirm_split_today()


    def action_confirm_split_first_month(self):
        self.ensure_one()
        if self.detail_id:
            today = fields.Date.today()
            first_day_current_month = today.replace(day=1)
            self.detail_id.action_split_line(first_day_current_month)
        return {'type': 'ir.actions.act_window_close'}

    def action_confirm_split_today(self):
        self.ensure_one()
        if self.detail_id:
            self.detail_id.action_split_line(fields.Date.today())
        return {'type': 'ir.actions.act_window_close'}
