from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    @api.constrains("parent_id")
    def _constrains_update_direct_manager_performance_evaluation(self):
        today = fields.Date.Date.context_today(self)
        first_day_of_last_month = today.replace(day=1) + relativedelta(months=-1)
        evaluation_obj = self.env["ngsc.hr.performance.evaluation"].sudo()
        for rec in self:
            _domain = [("date", "=", first_day_of_last_month),
                       ("employee_id", "=", rec.id),
                       ("state", "=", 'new')]
            evaluation_obj.search(_domain).write({"direct_manager_id": rec.sudo().parent_id.user_id.id})

    @api.constrains("indirect_manager")
    def _constrains_update_indirect_manager_performance_evaluation(self):
        today = fields.Date.Date.context_today(self)
        first_day_of_last_month = today.replace(day=1) + relativedelta(months=-1)
        evaluation_obj = self.env["ngsc.hr.performance.evaluation"].sudo()
        for rec in self:
            _domain = [("date", "=", first_day_of_last_month),
                       ("employee_id", "=", rec.id),
                       ("state", "=", 'new')]
            evaluation_obj.search(_domain).write({"indirect_manager_id": rec.sudo().indirect_manager.user_id.id})

    @api.model
    def cron_generate_task_evaluation(self, date=False):
        project_task_obj = self.env["project.task"].sudo()
        nonproject_task_obj = self.env["en.nonproject.task"].sudo()
        task_evaluation_obj = self.env["task.evaluation"].sudo()
        exclude_obj = self.env["ngsc.hr.performance.evaluation.exclude"].sudo()
        if date:
            evaluation_date = fields.Date.from_string(date)
        else:
            evaluation_date = fields.Date.Date.context_today(self)
        first_day_of_month = evaluation_date.replace(day=1) + relativedelta(months=-1)
        last_day_of_month = first_day_of_month + relativedelta(months=1, days=-1)
        task_evaluations = task_evaluation_obj.search([("date_evaluation", "=", first_day_of_month)])
        generated_project_tasks = task_evaluations.mapped("project_task_id.id")
        generated_nonproject_tasks = task_evaluations.mapped("nonproject_task_id.id")
        employee_exclude_ids = exclude_obj.get_performance_evaluation_exclude_employee(date=last_day_of_month)
        _domain_project_task = [("id", "not in", generated_project_tasks),
                                ("en_start_date", "<=", last_day_of_month),
                                ("date_deadline", ">=", first_day_of_month),
                                ("category", "=", "task"),
                                ("en_handler.employee_ids.en_status_hr", "=", 'active'),
                                ("en_handler.employee_ids", "not in", employee_exclude_ids),
                                ("stage_id.en_mark", "!=", "b"),
                                ("project_wbs_state", "=", "approved")]
        _domain_nonproject_task = [("id", "not in", generated_nonproject_tasks),
                                   ("en_pic_id.employee_ids", "not in", employee_exclude_ids),
                                   ("en_pic_id.employee_ids.en_status_hr", "=", 'active'),
                                   ("en_start_date", "<=", last_day_of_month),
                                   ("en_end_date", ">=", first_day_of_month)]
        project_tasks = project_task_obj.search(_domain_project_task)
        nonproject_tasks = nonproject_task_obj.search(_domain_nonproject_task)
        related_tasks = project_tasks.mapped("task_old_related_id.id")
        old_task_evaluations = task_evaluation_obj.search([("date_evaluation", "=", first_day_of_month),("project_task_id", "in", related_tasks)])
        old_data = []
        if old_task_evaluations:
            old_data = [{"project_task_id": l.id, "date_confirm": l.date_confirm, "evaluation": l.evaluation, "state": l.state, "is_locked": l.is_locked} for l in old_task_evaluations]
            old_task_evaluations.unlink()
        old_data_map = {rec["project_task_id"]: rec for rec in old_data}
        evaluation_values = []
        for line in project_tasks:
            vals = {
                "date_evaluation": first_day_of_month,
                "project_task_id": line.id,
            }
            old_rec = old_data_map.get(line.task_old_related_id.id)
            if old_rec:
                vals.update({
                    "date_confirm": old_rec["date_confirm"],
                    "evaluation": old_rec["evaluation"],
                    "state": old_rec["state"],
                    "is_locked": old_rec["is_locked"],
                })
            evaluation_values.append(vals)
        evaluation_values += [{"date_evaluation": first_day_of_month, "nonproject_task_id": line.id} for line in nonproject_tasks]
        task_evaluation_obj.create(evaluation_values)
        task_evaluation_obj.search(['|',("project_task_id.en_start_date", ">", str(last_day_of_month)),
                                    ("project_task_id.date_deadline", "<", str(first_day_of_month)),
                                    ("date_evaluation", "=", first_day_of_month),
                                    ("state", "=", 'not_evaluated'),
                                    ("is_locked", "=", False)]).unlink()
        task_evaluation_obj.search(['|', ("nonproject_task_id.en_start_date", ">", str(last_day_of_month)),
                                    ("nonproject_task_id.en_end_date", "<", str(first_day_of_month)),
                                    ("date_evaluation", "=", first_day_of_month),
                                    ("state", "=", 'not_evaluated'),
                                    ("is_locked", "=", False)]).unlink()

    @api.model
    def cron_generate_hr_performance_evaluation(self, date=False):
        evaluation_obj = self.env["ngsc.hr.performance.evaluation"].sudo()
        exclude_obj = self.env["ngsc.hr.performance.evaluation.exclude"].sudo()
        task_evaluation_obj = self.env["task.evaluation"].sudo()
        if date:
            evaluation_date = fields.Date.from_string(date)
        else:
            evaluation_date = fields.Date.Date.context_today(self)
        first_day_of_month = evaluation_date.replace(day=1) + relativedelta(months=-1)
        last_day_of_month = first_day_of_month + relativedelta(months=1, days=-1)
        generated_employees = evaluation_obj.search([("date", "=", first_day_of_month)]).mapped("employee_id.id")
        employee_exclude_ids = exclude_obj.get_performance_evaluation_exclude_employee(date=last_day_of_month)
        _domain = [("en_status_hr", "=", "active"),
                   ("en_internal_ok", "=", True),
                   ("en_date_start", "<=", last_day_of_month),
                   ("check_timesheet_before_checkout", "=", True),
                   ("id", "not in", generated_employees),
                   ("id", "not in", employee_exclude_ids)]
        employees = self.sudo().search(_domain)
        if not employees:
            return False
        values = []
        self._lock_data_task_evaluation(date_evaluation=first_day_of_month)
        for employee in employees:
            _domain_project = [("user_id", "=", employee.user_id.id),
                               ("project_task_id", "!=", False),
                               ("project_task_id.category", "=", "task"),
                               ("project_task_id.stage_id.en_mark", "!=", "b"),
                               ("project_task_id.project_wbs_state", "=", "approved"),
                               ("date_evaluation", "=", first_day_of_month),
                               ("is_locked", "=", True)]
            _domain_nonproject = [("user_id", "=", employee.user_id.id),
                                  ("nonproject_task_id", "!=", False),
                                  ("date_evaluation", "=", first_day_of_month),
                                  ("is_locked", "=", True)]
            tasks = task_evaluation_obj.search(_domain_project)
            tasks += task_evaluation_obj.search(_domain_nonproject)
            evaluation_task_ids = [(0, 0, {"task_evaluation_id": line.id}) for line in tasks]
            values.append({
                "employee_id": employee.id,
                "date": first_day_of_month,
                "en_block_id": employee.en_block_id.id,
                "department_id": employee.department_id.id,
                "en_department_id": employee.en_department_id.id,
                "direct_manager_id": employee.parent_id.user_id.id,
                "indirect_manager_id": employee.indirect_manager.user_id.id,
                "evaluation_task_ids": evaluation_task_ids
            })
        result = evaluation_obj.create(values)
        return result

    def _lock_data_task_evaluation(self, date_evaluation=False):
        if self._context.get("refresh", False):
            return
        now = fields.Datetime.now()
        _domain = [("date_evaluation", "=", date_evaluation)]
        records = self.env["task.evaluation"].sudo().search(_domain)
        records.write({"is_locked": True, "datetime_locked": now})


