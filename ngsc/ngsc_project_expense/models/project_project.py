from datetime import timedelta, date
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class Project(models.Model):
    _inherit = "project.project"

    en_bmm_stage_ids = fields.One2many("en.bmm.stage", "project_id", string="BMM theo giai đoạn")
    bmm_os = fields.Float(string="BMM OS", tracking=True)
    expense_os = fields.Monetary(string="Chi phí", currency_field="company_currency", tracking=True)
    company_currency = fields.Many2one("res.currency", string="Currency", compute="_compute_company_currency")

    def _compute_company_currency(self):
        for rec in self:
            rec.company_currency = self.env.company.currency_id.id

    def _compute_en_bmm_ids(self):
        # Bỏ logic sinh tự động các tháng BMM
        return

    @api.model
    def create(self, values):
        res = super(Project, self).create(values)
        if res.en_bmm_stage_ids:
            res.action_update_bmm_expense()
            res._update_resource_expense()
        return res

    def write(self, vals):
        res = super(Project, self).write(vals)
        if 'en_bmm_stage_ids' in vals or 'date_start' in vals or 'date' in vals:
            self.action_update_bmm_expense()
            self._update_resource_expense()
        return res

    def action_update_bmm_expense(self):
        self._update_bmm_expense_week()
        self._generate_bmm_expense_month()

    def _update_bmm_expense_week(self):
        for rec in self:
            if not rec.date_start or not rec.date:
                continue
            current_start = rec.date_start
            overall_end = rec.date
            for stage in rec.en_bmm_stage_ids.sorted('id'):
                if not current_start or (overall_end and current_start > overall_end):
                    break
                weeks = stage.number_of_week or 0
                stage_start = current_start
                stage_end = stage_start + timedelta(weeks=weeks) - timedelta(days=1)
                if overall_end and stage_end > overall_end:
                    stage_end = overall_end
                stage.date_start = stage_start
                stage.date_end = stage_end
                current_start = stage_end + timedelta(days=1)

    @staticmethod
    def _working_days_between(start_date, end_date):
        current = start_date
        working_days = []
        while current <= end_date:
            if current.weekday() < 5:
                working_days.append(current)
            current += timedelta(days=1)
        return working_days

    def _generate_bmm_expense_month(self):
        for rec in self:
            data_per_month = {}
            valid_months = set()
            for line in rec.en_bmm_stage_ids:
                start = line.date_start
                end = line.date_end
                if not start or not end:
                    continue
                total_working_days = len(self._working_days_between(start, end))
                if total_working_days == 0:
                    continue
                current_month = start.replace(day=1)
                while current_month <= end:
                    next_month = current_month + relativedelta(months=1)
                    month_end = next_month - timedelta(days=1)
                    period_start = max(start, current_month)
                    period_end = min(end, month_end)
                    working_days_in_month = len(self._working_days_between(period_start, period_end))
                    proportion = working_days_in_month / total_working_days
                    bmm_to_add = (line.bmm or 0) * proportion
                    expense_to_add = (line.expense or 0) * proportion
                    if current_month not in data_per_month:
                        data_per_month[current_month] = {'bmm': 0, 'expense': 0}
                    data_per_month[current_month]['bmm'] += round(bmm_to_add, 3)
                    data_per_month[current_month]['expense'] += round(expense_to_add, 3)
                    valid_months.add(current_month)
                    current_month = next_month
            old_bmm_ids = self.env['en.bmm'].search([('project_id', '=', rec.id)])
            for bmm in old_bmm_ids:
                if bmm.date not in valid_months:
                    bmm.unlink()
            for month_date, values in data_per_month.items():
                existing = self.env['en.bmm'].search([
                    ('date', '=', month_date),
                    ('project_id', '=', rec.id)
                ], limit=1)
                if existing:
                    existing.bmm = round(values['bmm'], 3)
                    existing.expense = round(values['expense'], 3)
                else:
                    self.env['en.bmm'].create({
                        'project_id': rec.id,
                        'date': month_date,
                        'month_txt': month_date.strftime('%m/%Y'),
                        'bmm': round(values['bmm'], 3),
                        'expense': round(values['expense'], 3)
                    })

    def button_create_project_decision(self):
        action = super().button_create_project_decision()
        action['context'] = dict(action.get('context', {}))
        action['context']['default_en_bmm'] = round(sum(self.en_bmm_ids.mapped("bmm")),3) + self.bmm_os
        action['context']['default_bmm_os'] = self.bmm_os
        action['context']['default_expense_os'] = self.expense_os
        return action

    def _update_resource_expense(self):
        resource_plans = self.en_resource_ids.filtered(lambda x: x.state not in ['refused', 'expire'])
        for r in resource_plans:
            r.with_delay()._update_resource_planing_expense()