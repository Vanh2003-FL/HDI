from datetime import datetime, time
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models


class QualityDetail(models.Model):
    _inherit = "en.quality.detail"

    en_mm = fields.Float(string='MM', compute_sudo=True, readonly=False, compute='_compute_en_mm', store=True)

    # Update logic mới mm_rate
    @api.depends('employee_id', 'date_start', 'date_end', 'workload')
    def _compute_en_mm(self):
        technical_obj = self.env["en.technical.model"].sudo()
        for rec in self:
            if not (rec.employee_id and rec.date_start and rec.date_end):
                rec.en_mm = 0
                continue
            hours_standard = rec.employee_id.resource_calendar_id.hours_per_day or 8
            net_working_day_months = technical_obj.count_net_working_days_by_months(rec.date_start, rec.date_end)
            total_mm = 0.0
            current_month = rec.date_start.replace(day=1)
            while current_month <= rec.date_end:
                next_month = current_month + relativedelta(months=1)
                d_from, d_to = max(rec.date_start, current_month), min(rec.date_end, next_month - relativedelta(days=1))
                hours = technical_obj.convert_daterange_to_hours(rec.employee_id,
                                                                 datetime.combine(d_from, time.min),
                                                                 datetime.combine(d_to, time.max))
                net_working_day = net_working_day_months.get(str(current_month), 22)
                total_mm += hours / hours_standard / net_working_day
                current_month = next_month
            rec.en_mm = total_mm * rec.workload


class QualityControl(models.Model):
    _inherit = "en.quality.control"

    # Update logic mới mm_rate
    @api.depends('order_line', 'order_line.en_md', 'order_line.en_mm')
    def _compute_total_md(self):
        for rec in self:
            total_md = 0
            total_mm = 0
            for line in rec.order_line:
                total_md += line.en_md
                total_mm += line.en_mm
            rec.total_md = round(total_md, 2)
            rec.total_mm = round(total_mm, 2)

    # Update logic mới mm_rate
    @api.depends('project_id.en_resource_id', 'project_id.en_resource_id.order_line')
    def _compute_mm_qa_project(self):
        for rec in self:
            total_mm = 0
            if rec.project_id.en_resource_id:
                for line in rec.project_id.en_resource_id.order_line.filtered(lambda x: x.employee_id.user_id == rec.project_id.en_project_qa_id):
                    total_mm += line.en_mm
            rec.mm_qa_project = round(total_mm, 2)