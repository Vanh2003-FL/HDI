from collections import defaultdict
from odoo import models, fields, api, _, exceptions
from odoo.exceptions import ValidationError


class ResourcePlaning(models.Model):
    _inherit = "en.resource.planning"

    def _auto_init(self):
        self._cr.execute("""alter table en_resource_planning
            add column if not exists total_budget_expense numeric,
            add column if not exists total_actual_expense numeric;""")
        return super()._auto_init()

    total_budget_expense = fields.Monetary(string="Tổng budget", currency_field="company_currency",
                                           compute="_compute_budget_expense", store=True,
                                           groups='ngsd_base.group_gdkv,ngsd_base.group_pm,ngsd_base.group_tptc,ngsd_base.group_tpvh,ngsd_base.group_tk,ngsd_base.group_tppmo')
    total_actual_expense = fields.Monetary(string="Tổng chi phí", currency_field="company_currency",
                                           compute="_compute_actual_expense", store=True,
                                           groups='ngsd_base.group_gdkv,ngsd_base.group_pm,ngsd_base.group_tptc,ngsd_base.group_tpvh,ngsd_base.group_tk,ngsd_base.group_tppmo')
    company_currency = fields.Many2one("res.currency", string="Currency", compute="_compute_company_currency")
    resource_expense_ids = fields.One2many("ngsc.resource.expense", "resource_planning_id",
                                           string="Chi phí theo giai đoạn")

    @api.depends("order_line", "order_line.expense")
    def _compute_actual_expense(self):
        for rec in self:
            rec.total_actual_expense = sum(x.expense for x in rec.order_line)

    @api.depends("project_id", "project_id.en_bmm_ids.expense", "project_id.en_bmm_ids")
    def _compute_budget_expense(self):
        for rec in self:
            rec.total_budget_expense = sum(x.expense for x in rec.project_id.en_bmm_ids)

    def _compute_company_currency(self):
        for lead in self:
            lead.company_currency = self.env.company.currency_id.id

    @api.depends("total_actual_expense", "total_budget_expense")
    def _compute_budget_over(self):
        for rec in self:
            if rec.total_budget_expense == 0:
                rec.budget_over = 0
            else:
                budget_over = (rec.total_actual_expense - rec.total_budget_expense) / rec.total_budget_expense
                rec.budget_over = max(([budget_over, 0]))

    def write(self, values):
        res = super(ResourcePlaning, self).write(values)
        if "order_line" in values:
            for rec in self:
                rec.with_delay()._update_resource_planing_expense()
        return res

    def _update_resource_planing_expense(self):
        self.resource_expense_ids.unlink()
        timesheet_obj = self.env["account.analytic.line"].sudo()
        bmm_project = self.env['en.bmm.stage'].sudo().search(
            [('project_id', '=', self.project_id.id), ('bmm_stage_id', '!=', False)], order='id asc')
        grouped = defaultdict(lambda: {
            'project_bmm': 0.0,
            'project_expense': 0.0,
            'planned_bmm': 0.0,
            'planned_expense': 0.0,
            'actual_bmm': 0.0,
            'actual_expense': 0.0,
        })
        for rec in bmm_project:
            grouped[rec.bmm_stage_id.id]['project_bmm'] += rec.bmm or 0.0
            grouped[rec.bmm_stage_id.id]['project_expense'] += rec.expense or 0.0
        values = []
        for line in self.order_line.filtered(lambda x: x.project_task_stage_id.bmm_stage_id):
            stage = line.project_task_stage_id.bmm_stage_id
            if stage:
                grouped[stage.id]['planned_bmm'] += line.en_md or 0.0
                grouped[stage.id]['planned_expense'] += line.expense or 0.0
            timesheets = timesheet_obj.search([("project_id", "=", self.project_id.id),
                                               ("task_id", "child_of",
                                                line.project_task_stage_id.id)])
            total_hours = 0
            for t in timesheets:
                if t.en_state == 'approved':
                    total_hours += t.unit_amount
                if t.ot_state == 'approved':
                    total_hours += t.ot_time
            grouped[stage.id]['actual_bmm'] += (total_hours / 8 / self.mm_rate) if self.mm_rate > 0 else 0.0
        for stage_id in sorted(grouped):
            values.append({
                'resource_planning_id': self.id,
                'project_id': self.project_id.id,
                'stage_id': stage_id,
                'project_bmm': round(grouped[stage_id]['project_bmm'], 2),
                'planned_bmm': round((grouped[stage_id]['planned_bmm'] / self.mm_rate), 2) if self.mm_rate > 0 else 0.0,
                'actual_bmm': round(grouped[stage_id]['actual_bmm'], 2),
                'project_expense': grouped[stage_id]['project_expense'],
                'planned_expense': grouped[stage_id]['planned_expense'],
                'actual_expense': 0.0,
            })
        self.env["ngsc.resource.expense"].sudo().create(values)
