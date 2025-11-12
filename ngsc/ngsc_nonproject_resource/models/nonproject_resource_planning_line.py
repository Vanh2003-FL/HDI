# -*- coding: utf-8 -*-
from datetime import datetime, time
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class NonprojectResourcePlaningLine(models.Model):
    _name = "ngsc.nonproject.resource.planning.line"
    _description = "Kế hoạch nguồn lực ngoài dự án chi tiết"

    planning_id = fields.Many2one("ngsc.nonproject.resource.planning", string="Kế hoạch",
                                  required=True, ondelete="cascade")
    employee_id = fields.Many2one("hr.employee", string="Họ và tên", required=True)
    work_email = fields.Char(string="Email", related="employee_id.work_email")
    project_workload = fields.Float(string="Workload Dự án", compute="_compute_project_workload", store=True)
    daily_workload = fields.Float(string="Workload hàng ngày")
    support_workload = fields.Float(string="Workload kinh doanh")
    presale_workload = fields.Float(string="Workload kinh Presale")
    support_project_workload = fields.Float(string="Workload hỗ trợ dự án")
    total_workload = fields.Float(string="Tổng Workload", compute="_compute_total_workload", store=True)
    total_nonproject_workload = fields.Float(string="Tổng Workload ngoài dự án", compute="_compute_total_workload", store=True)
    total_md = fields.Float(string="Tổng MD", compute="_compute_total_md_mm", store=True)
    total_mm = fields.Float(string="Tổng MM", compute="_compute_total_md_mm", store=True)
    total_nonproject_md = fields.Float(string="Tổng MD ngoài dự án", compute="_compute_total_md_mm", store=True)
    total_nonproject_mm = fields.Float(string="Tổng MM ngoài dự án", compute="_compute_total_md_mm", store=True)
    workload_project_description = fields.Html(string="Tooltip workload dự án", compute="_compute_project_workload", store=True)

    def _compute_project_workload(self):
        resource_obj = self.env["en.resource.detail"].sudo()
        technical_obj = self.env["en.technical.model"].sudo()
        for rec in self:
            first_day_of_month = rec.planning_id.date
            last_day_of_month = first_day_of_month + relativedelta(months=1, days=-1)
            results = technical_obj.count_net_working_days_by_months(first_day_of_month, last_day_of_month)
            net_working_day = results[str(first_day_of_month)]
            _domain = [("order_id.state", "=", "approved"),
                       ("employee_id", "=", rec.employee_id.id),
                       ("date_start", "<=", last_day_of_month),
                       ("date_end", ">=", first_day_of_month)]
            employee_resources = resource_obj.search(_domain)
            hours_total = 0
            descriptions = []
            for resource in employee_resources:
                date_from = max([first_day_of_month, resource.date_start])
                date_to = min([resource.date_end, last_day_of_month])
                datetime_from = datetime.combine(date_from, time.min)
                datetime_to = datetime.combine(date_to, time.max)
                hours_total += resource.workload * technical_obj.convert_daterange_to_hours(rec.employee_id, datetime_from, datetime_to)

                workload_percent = resource.workload * 100
                date_start = datetime.strftime(resource.date_start, '%d/%m/%Y') if resource.date_start else ""
                date_end = datetime.strftime(resource.date_end, '%d/%m/%Y') if resource.date_end else ""
                if workload_percent.is_integer():
                    workload_str = f"{int(workload_percent)}%"
                else:
                    workload_str = f"{workload_percent:.2f}%"
                msg = f"<li>Dự án {resource.order_id.project_id.name} ({date_start} - {date_end}) workload: {workload_str}</li>"
                descriptions.append(msg)
            rec.project_workload = hours_total / 8 / net_working_day if net_working_day > 0 else 0
            rec.workload_project_description = f"<ul>{''.join(descriptions)}</ul>" if descriptions else ""

    @api.depends("project_workload", "daily_workload", "support_workload", "presale_workload",
                 "support_project_workload")
    def _compute_total_workload(self):
        for rec in self:
            data_total = [rec.project_workload, rec.daily_workload, rec.support_workload, rec.presale_workload,
                    rec.support_project_workload]
            data_nonproject = [rec.daily_workload, rec.support_workload, rec.presale_workload, rec.support_project_workload]
            rec.total_workload = sum(data_total)
            rec.total_nonproject_workload = sum(data_nonproject)

    @api.depends("total_workload", "total_nonproject_workload")
    def _compute_total_md_mm(self):
        technical_obj = self.env["en.technical.model"].sudo()
        for rec in self:
            first_day_of_month = rec.planning_id.date
            last_day_of_month = first_day_of_month + relativedelta(months=1, days=-1)
            results = technical_obj.count_net_working_days_by_months(first_day_of_month, last_day_of_month)
            net_working_day = results[str(first_day_of_month)]
            rec.total_md = round((rec.total_workload * net_working_day), 2)
            rec.total_mm = round(rec.total_workload, 2)
            rec.total_nonproject_md = round((rec.total_nonproject_workload * net_working_day), 2)
            rec.total_nonproject_mm = round(rec.total_nonproject_workload, 2)