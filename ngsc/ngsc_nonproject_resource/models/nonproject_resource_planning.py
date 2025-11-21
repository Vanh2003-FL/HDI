# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _, exceptions
from odoo.exceptions import ValidationError, UserError, AccessError


class NonprojectResourcePlaning(models.Model):
    _name = "ngsc.nonproject.resource.planning"
    _rec_name = "department_id"
    _description = "Kế hoạch nguồn lực ngoài dự án"

    department_id = fields.Many2one("hr.department", string="Trung tâm", required=True)
    date = fields.Date(string="Thời gian", required=True)
    month_display = fields.Char(string="Tháng kế hoạch", compute="_compute_month_display", store=True)
    state = fields.Selection(string="Trạng thái", default="active",
                             selection=[('active', 'Đang hiệu lực'),
                                        ('inactive', 'Hết hiệu lực')])
    planning_line_ids = fields.One2many("ngsc.nonproject.resource.planning.line", "planning_id",
                                        string="Chi tiết nguồn lực")
    total_md = fields.Float(string="Tổng nguồn lực (MD)", compute="_compute_total_md_mm", store=True)
    total_mm = fields.Float(string="Tổng nguồn lực (MM)", compute="_compute_total_md_mm", store=True)

    @api.depends("date")
    def _compute_month_display(self):
        for rec in self:
            month_display = False
            if rec.date:
                month = f"{rec.date.month:02d}"
                year = str(rec.date.year)
                month_display = f"{month}/{year}"
            rec.month_display = month_display

    @api.depends("planning_line_ids", "planning_line_ids.total_md", "planning_line_ids.total_mm")
    def _compute_total_md_mm(self):
        for rec in self:
            rec.total_md = round(sum(rec.planning_line_ids.mapped("total_md")), 2)
            rec.total_mm = round(sum(rec.planning_line_ids.mapped("total_mm")), 2)

    @api.model
    def cron_generate_department_resource_planning(self, date=False):
        if date:
            evaluation_date = fields.Date.from_string(date)
        else:
            evaluation_date = fields.Date.Date.context_today(self)
        department_obj = self.env["hr.department"].sudo()
        employee_obj = self.env["hr.employee"].sudo()
        exclude_obj = self.env["nonproject.resource.planning.exclude"].sudo()
        start_this_month = evaluation_date.replace(day=1)
        end_this_month = start_this_month + relativedelta(months=1, days=-1)
        start_last_month = start_this_month - relativedelta(months=1)

        exclude_employee_ids, exclude_department_ids = exclude_obj.get_nonproject_resource_planning_exclude_employee(date=end_this_month)
        exclude_department_ids += self.sudo().search([("date", "=", start_this_month)]).mapped("department_id")
        exclude_employee_ids += employee_obj.search([("en_status_hr", "=", "inactive"),
                                                     ("active", "=", False),
                                                     ("departure_date", "<", str(start_this_month)),
                                                     ('en_internal_ok', '=', True)])
        departments = department_obj.search([("id", "not in", exclude_department_ids.ids)])

        data_last_month = self.sudo().search([("date", "=", start_last_month), ("department_id", "in", departments.ids)])
        results = data_last_month.action_copy_resource_planning(date=start_this_month)
        self.sudo().search([("date", "=", start_last_month)]).write({"state": "inactive"})
        departments -= data_last_month.mapped("department_id")
        values = [{"department_id": dept.id, "date": start_this_month} for dept in departments]
        if values:
            results += self.sudo().create(values)
        for r in results:
            r.with_context(ctx_cronjob=True).action_refresh_resource_planing_detail(exclude_employee_ids)

    def action_copy_resource_planning(self, date=False):
        results = self.env["ngsc.nonproject.resource.planning"]
        for rec in self:
            new_record = rec.copy(default={'date': date})
            for line in rec.planning_line_ids:
                line.copy(default={'planning_id': new_record.id})
            results += new_record
        return results

    def action_refresh_resource_planing_detail(self, exclude_employee_ids=[]):
        exclude_obj = self.env["nonproject.resource.planning.exclude"].sudo()
        planning_detail_obj = self.env["ngsc.nonproject.resource.planning.line"]
        employee_obj = self.env["hr.employee"].with_context(active_test=False).sudo()
        if not exclude_employee_ids:
            last_day_of_month = self.date + relativedelta(day=1, months=1, days=-1)
            exclude_employee_ids, exclude_department_ids = exclude_obj.get_nonproject_resource_planning_exclude_employee(
                date=last_day_of_month)
            exclude_employee_ids += employee_obj.search([("department_id", "=", self.department_id.id),
                                                 ("en_status_hr", "=", "inactive"),
                                                 ("active", "=", False),
                                                 ("departure_date", "<", str(self.date)),
                                                 ('en_internal_ok', '=', True)])
            planning_detail_obj.search([("planning_id", "=", self.id),
                                        ("employee_id", "in", exclude_employee_ids.ids)]).unlink()
        exclude_employee_ids += self.planning_line_ids.mapped("employee_id")
        employee_ids = employee_obj.search([("department_id", "=", self.department_id.id),
                                            ("en_status_hr", "=", "active"),
                                            ("active", "=", True),
                                            ('en_internal_ok', '=', True),
                                            ("id", "not in", exclude_employee_ids.ids)])
        employee_ids += employee_obj.with_context(active_test=False).search([("department_id", "=", self.department_id.id),
                                            ("en_status_hr", "=", "inactive"),
                                            ("active", "=", False),
                                            ("departure_date", ">=", str(self.date)),
                                            ('en_internal_ok', '=', True),
                                            ("id", "not in", exclude_employee_ids.ids)])
        values = [{"employee_id": emp.id, "planning_id": self.id} for emp in employee_ids]
        planning_detail_obj.create(values)
        self.planning_line_ids._compute_project_workload()
        if not self._context.get("ctx_cronjob", False):
            msg = self.check_resource_overload()
            self.env.user.notify_success("Làm mới dữ liệu nguồn lực thành công.")
            if msg:
                self.env.user.notify_warning(message=msg, sticky=True)

    def action_view_resource_info(self):
        context = {
            'default_department_ids': self.department_id.ids,
            'default_resource_nonproject_planing_id': self.id
        }
        return self.open_form_or_tree_view('ngsc_nonproject_resource.resource_nonproject_account_report_wizard_act',
                                           False, False, context, 'Thông tin nguồn lực tổng', 'new')

    @api.constrains("planning_line_ids")
    def _check_planning_line_ids(self):
        msg = self.check_resource_overload()
        if not msg:return
        raise ValidationError(msg)

    def check_resource_overload(self):
        maximum_workload_percent = int(self.env['ir.config_parameter'].sudo().get_param('maximum_workload')) or 100
        maximum_workload = maximum_workload_percent / 100
        employee_name, msg = [], ""
        for rec in self.planning_line_ids:
            if rec.total_workload <= maximum_workload:
                continue
            workload_percent = rec.total_workload * 100
            employee_name.append(
                f"{rec.employee_id.name} ({int(workload_percent) if workload_percent.is_integer() else workload_percent}%)")
        if employee_name:
            employees = '• ' + '\n• '.join(employee_name)
            msg = (f"Workload của những nhân sự dưới đây vượt quá % Workload cho phép ({maximum_workload_percent}%). Vui lòng điều chỉnh lại.\n"
                   f"{employees}")
        return msg
