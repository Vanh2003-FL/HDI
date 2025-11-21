from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _, exceptions
from odoo.exceptions import ValidationError

task_type_compare = {
    "daily": "daily_workload",
    "support": "support_workload",
    "waiting_task": "waiting_task",
    "presale": "presale_workload",
    "support_project": "support_project_workload",
}


class NonProjectTask(models.Model):
    _inherit = "account.analytic.line"

    @api.constrains("en_nonproject_task_id", "employee_id", "unit_amount", "date", "en_nonproject_task_id.en_task_type")
    def _constrains_nonproject_timesheet(self):
        technical_obj = self.env["en.technical.model"].sudo()
        timesheet_obj = self.env["account.analytic.line"].sudo()
        resource_obj = self.env["ngsc.nonproject.resource.planning.line"].sudo()
        range_date = self.mapped("date")
        results = technical_obj.count_net_working_days_by_months(min(range_date), max(range_date))
        for rec in self:
            if not rec.date or not rec.employee_id or not rec.en_nonproject_task_id or rec.en_nonproject_task_id.en_task_type == "waiting_task":
                continue
            first_day_of_month = rec.date.replace(day=1)
            last_day_of_month = first_day_of_month + relativedelta(months=1, days=-1)
            net_working_day = results[str(first_day_of_month)]
            _domain_timesheet = [("date", ">=", str(first_day_of_month)),
                                 ("date", "<=", str(last_day_of_month)),
                                 ("employee_id", "=", rec.employee_id.id),
                                 ("en_nonproject_task_id", "!=", False),
                                 ("en_nonproject_task_id.en_task_type", "=", rec.en_nonproject_task_id.en_task_type),
                                 ("en_state", "!=", 'cancel')]
            timesheets = timesheet_obj.search(_domain_timesheet)
            total_hours = sum(timesheets.mapped("unit_amount"))
            _domain_employee_planning = [("planning_id.date", "=", str(first_day_of_month)),
                                         ("planning_id.department_id", "=", rec.employee_id.department_id.id),
                                         ("employee_id", "=", rec.employee_id.id)]
            employee_resource = resource_obj.search(_domain_employee_planning, order="id desc", limit=1)
            if not employee_resource:continue
            work_load_type = task_type_compare.get(rec.en_nonproject_task_id.en_task_type)
            workload = employee_resource.read([work_load_type])[0].get(work_load_type)
            resource_hours = workload * net_working_day * 8
            if total_hours >resource_hours:
                message = "Số giờ khai Timesheet ngoài dự án vượt quá số giờ dự kiến trong kế hoạch"
                self.env.user.notify_warning(message, "Cảnh báo")