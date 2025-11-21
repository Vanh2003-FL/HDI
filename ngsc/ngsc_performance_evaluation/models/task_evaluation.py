# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _, exceptions
from odoo.exceptions import ValidationError, UserError, AccessError
from ..utils.constant import *
from ..utils.query import *
task_type_compare = {
    "daily": "daily_workload",
    "support": "support_workload",
    "waiting_task": "waiting_task",
    "presale": "presale_workload",
    "support_project": "support_project_workload",
}

class TaskEvaluation(models.Model):
    _name = "task.evaluation"
    _order = "date_evaluation desc"
    _description = "Đánh giá chất lượng công việc"

    name = fields.Char(string="Tên công việc", compute="_compute_task_name", store=True)
    project_task_id = fields.Many2one("project.task", string="Công việc")
    nonproject_task_id = fields.Many2one("en.nonproject.task", string="Công việc ngoài dự án")
    date_evaluation = fields.Date(string="Thời gian tháng đánh giá")
    month_evaluation = fields.Char(string="Tháng đánh giá", compute="_compute_month_evaluation", store=True)
    date_confirm = fields.Date(string="Ngày đánh giá")
    user_id = fields.Many2one("res.users", string="Người chịu trách nhiệm", compute="_compute_user_reviewer_id",
                              store=True)
    employee_id = fields.Many2one("hr.employee",string="Nhân viên", compute="_compute_employee_id",
                              store=True)
    reviewer_id = fields.Many2one("res.users", string="Người đánh giá", compute="_compute_user_reviewer_id", store=True)
    evaluation = fields.Selection(string="Đánh giá chất lượng", selection=task_evaluation_options, index=True)
    state = fields.Selection(string="Trạng thái", default="not_evaluated", index=True,
                             selection=[('evaluated', 'Đã đánh giá'),
                                        ('not_evaluated', 'Chưa đánh giá'),
                                        ('evaluated_again', 'Đánh giá lại'), ('cancel', 'Đã hủy')])
    date_start = fields.Date(string="Ngày bắt đầu", compute="_compute_task_date", store=True)
    date_end = fields.Date(string="Ngày kết thúc", compute="_compute_task_date", store=True)
    hour_actual = fields.Float(string="Số giờ thực hiện", compute="_compute_hour_actual", store=True)
    hour_actual_resource = fields.Float(string="Số giờ ghi nhận", compute="_compute_hour_actual", store=True)
    is_reviewer = fields.Boolean(compute='_compute_is_reviewer')
    is_locked = fields.Boolean(string="Khóa dữ liệu", default=False, readonly=True)
    datetime_locked = fields.Datetime(string="Thời gian khóa dữ liệu")
    project_id = fields.Many2one("project.project", string="Dự án", related="project_task_id.project_id", store=True)
    en_task_type = fields.Selection([
        ('daily', 'Công việc hàng ngày'),
        ('support', 'Công việc kinh doanh'),
        ('waiting_task', 'Công việc trong dự án đang chờ'),
        ('presale', 'Công việc Presale'),
        ('support_project', 'Công việc hỗ trợ dự án')
    ], string='Loại việc', related="nonproject_task_id.en_task_type", store=True)
    evaluation_task_ids = fields.One2many("ngsc.hr.performance.evaluation.task", "task_evaluation_id",
                                          string="Công việc đánh giá")
    unit_id = fields.Many2one("ngsc.unit.hierarchy", string="Phân cấp phòng ban", index=True,
                              compute="_compute_unit", store=True)

    @api.depends("employee_id", "employee_id.en_department_id", "employee_id.department_id", "employee_id.en_block_id")
    def _compute_unit(self):
        self.flush()
        for rec in self:
            if not rec.employee_id:
                rec.unit_id = False
                continue
            self.env.cr.execute(QUERY_GET_UNIT_HIERARCHY % rec.employee_id.id)
            unit_id = self.env.cr.fetchone()[0] or False
            rec.unit_id = unit_id

    @api.depends("user_id")
    def _compute_employee_id(self):
        for rec in self:
            rec.employee_id = rec.user_id.employee_id.id

    @api.depends("project_task_id", "nonproject_task_id", "project_task_id.name", "nonproject_task_id.name")
    def _compute_task_name(self):
        for rec in self:
            if rec.project_task_id:
                rec.name = rec.project_task_id.name or ""
            else:
                rec.name = rec.nonproject_task_id.name or ""

    @api.depends_context('uid')
    def _compute_is_reviewer(self):
        current_user = self.env.user
        for rec in self:
            rec.is_reviewer = (rec.reviewer_id == current_user)

    @api.depends("date_evaluation")
    def _compute_month_evaluation(self):
        for rec in self:
            rec.month_evaluation = rec.date_evaluation.strftime("%m-%Y") if rec.date_evaluation else ""

    @api.depends("project_task_id", "nonproject_task_id",
                 "project_task_id.en_handler", "nonproject_task_id.en_pic_id",
                 "project_task_id.en_supervisor", "nonproject_task_id.en_supervisor_id")
    def _compute_user_reviewer_id(self):
        for rec in self:
            if rec.project_task_id:
                rec.reviewer_id = rec.project_task_id.en_supervisor.id
                rec.user_id = rec.project_task_id.en_handler.id
            else:
                rec.reviewer_id = rec.nonproject_task_id.en_supervisor_id.id
                rec.user_id = rec.nonproject_task_id.en_pic_id.id

    def action_confirm(self):
        today = fields.Date.Date.context_today(self)
        empty_records = self.filtered(lambda x: not x.evaluation and x.state in ["not_evaluated", "evaluated_again"])

        if empty_records:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Vui lòng nhập Đánh giá chất lượng trước khi xác nhận!"),
                    "type": "warning",
                    "sticky": False,  # Tự ẩn sau 5s
                }
            }

        for rec in self.filtered(lambda x: x.state in ["not_evaluated", "evaluated_again"]):
            if rec.is_locked:
                raise ValidationError(_("Bạn ghi đánh giá tháng %s đã bị khóa.") % rec.month_evaluation)
            if not rec.is_reviewer:
                raise UserError(_("Chỉ có người đánh giá được phép đánh giá công việc."))

            rec.write({
                "state": "evaluated",
                "date_confirm": today,
                "is_locked": True,
                "datetime_locked": fields.Datetime.now(),
            })

            rec.sudo().evaluation_task_ids._compute_task_evaluation()

            if not rec.evaluation_task_ids.mapped("task_evaluation_id").filtered(lambda x: x.state != "evaluated") \
                    and rec.evaluation_task_ids:
                rec.sudo().evaluation_task_ids[0].performance_evaluation_id.write({"state": "new"})

    def action_cancel(self):
        today = fields.Date.Date.context_today(self)
        for rec in self.filtered(lambda x: x.state in ["not_evaluated", "evaluated_again", 'cancel']):
            if rec.state == "cancel":
                raise UserError("Không thể Hủy bản ghi đang ở trạng thái Hủy.")
            if rec.is_locked:
                raise ValidationError(f"Bạn ghi đánh giá tháng {rec.month_evaluation} đã bị khóa.")
            if not rec.is_reviewer:
                raise UserError("Chỉ có người đánh giá được phép Hủy đánh giá.")

            rec.write({"state": "cancel",
                       "date_confirm": today,
                       "is_locked": True,
                       "hour_actual": 0,
                       "hour_actual_resource":0,
                       "evaluation": False,
                       "datetime_locked": fields.Datetime.now()})

    @api.depends("project_task_id", "nonproject_task_id", "date_evaluation")
    def _compute_task_date(self):
        for rec in self:
            last_day_of_month = rec.date_evaluation + relativedelta(day=1, months=1, days=-1)
            if rec.project_task_id:
                date_start_task = rec.project_task_id.en_start_date
                date_end_task = rec.project_task_id.date_deadline
                rec.date_start = rec.date_evaluation if date_start_task and str(date_start_task) <= str(rec.date_evaluation) else date_start_task
                rec.date_end = last_day_of_month if date_end_task and str(date_end_task) > str(last_day_of_month) else date_end_task
            else:
                date_start_task = rec.nonproject_task_id.en_start_date
                date_end_task = rec.nonproject_task_id.en_end_date
                rec.date_start = rec.date_evaluation if date_start_task and str(date_start_task) <= str(rec.date_evaluation) else date_start_task
                rec.date_end = last_day_of_month if date_end_task and str(date_end_task) > str(last_day_of_month) else date_end_task

    @api.depends("project_task_id", "nonproject_task_id", "date_start", "date_end")
    def _compute_hour_actual(self):
        technical_obj = self.env["en.technical.model"].sudo()
        resource_obj = self.env["ngsc.nonproject.resource.planning.line"].sudo()
        range_date = self.mapped("date_evaluation")
        results = technical_obj.count_net_working_days_by_months(min(range_date), max(range_date))
        for rec in self:
            hour_actual_resource = 0
            if rec.project_task_id:
                timesheets = rec.project_task_id.timesheet_ids.filtered(
                    lambda x: x.en_state in ['approved','waiting'] and rec.date_start and rec.date_end and rec.date_start <= x.date <= rec.date_end)
                ot_timesheets = rec.project_task_id.timesheet_ids.filtered(
                    lambda x: x.ot_state == 'approved' and rec.date_start and rec.date_end and rec.date_start <= x.date <= rec.date_end)
                total_hours = sum(timesheets.mapped('unit_amount')) + sum(ot_timesheets.mapped('ot_time'))
                rec.hour_actual = total_hours
                rec.hour_actual_resource = total_hours
            else:
                timesheets = rec.nonproject_task_id.timesheet_ids.filtered(
                    lambda x: x.en_state in ['approved','waiting'] and rec.date_start and rec.date_end and rec.date_start <= x.date <= rec.date_end)
                total_hours = sum(timesheets.mapped('unit_amount'))
                if rec.en_task_type != "waiting_task":
                    hour_actual_resource = total_hours
                    _domain_employee_planning = [("planning_id.date", "=", str(rec.date_evaluation)),
                                                 ("planning_id.department_id", "=", rec.employee_id.department_id.id),
                                                 ("employee_id", "=", rec.employee_id.id)]
                    employee_resource = resource_obj.search(_domain_employee_planning, order="id desc", limit=1)
                    net_working_day = results[str(rec.date_evaluation)]
                    if employee_resource:
                        work_load_type = task_type_compare.get(rec.en_task_type)
                        workload = employee_resource.read([work_load_type])[0].get(work_load_type)
                        maximum_hours = workload * net_working_day * 8
                        hour_actual_resource = maximum_hours if hour_actual_resource > maximum_hours else hour_actual_resource
                ot_timesheets = rec.nonproject_task_id.timesheet_ids.filtered(
                    lambda x: x.ot_state == 'approved' and rec.date_start and rec.date_end and rec.date_start <= x.date <= rec.date_end)
                hours_ot = sum(ot_timesheets.mapped('ot_time'))
                total_hours += hours_ot
                hour_actual_resource += hours_ot
                rec.hour_actual = total_hours
                rec.hour_actual_resource = hour_actual_resource

    @api.model
    def cron_remind_reviewer_task_evaluation(self, date=False):
        if date:
            evaluation_date = fields.Date.from_string(date)
        else:
            evaluation_date = fields.Date.Date.context_today(self)
        first_day_of_month = evaluation_date.replace(day=1) + relativedelta(months=-1)
        task_evaluation_obj = self.env["task.evaluation"].sudo()
        _domain_project = [("project_task_id", "!=", False),
                           ("project_task_id.category", "=", "task"),
                           ("project_task_id.stage_id.en_mark", "!=", "b"),
                           ("project_task_id.project_wbs_state", "=", "approved"),
                           ("date_evaluation", "=", first_day_of_month),
                           ("state", "=", "not_evaluated")]
        _domain_nonproject = [("nonproject_task_id", "!=", False),
                              ("date_evaluation", "=", first_day_of_month),
                              ("state", "=", "not_evaluated")]

        project_tasks = task_evaluation_obj.search(_domain_project)
        nonproject_tasks = task_evaluation_obj.search(_domain_nonproject)

        project_reviewers = project_tasks.mapped("reviewer_id")
        nonproject_reviewers = nonproject_tasks.mapped("reviewer_id")

        mail_template = self.env.ref('ngsc_performance_evaluation.task_evaluation_remind_reviewer_mail_template')
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        project_action = self.env.ref('project.open_view_project_all')
        project_url = f"{base_url}/web#action={project_action.id}&model=project.project&view_type=kanban"

        nonproject_action = self.env.ref('ngsd_base.en_nonproject_task_all_action')
        nonproject_url = f"{base_url}/web#action={nonproject_action.id}&model=en.nonproject.task&view_type=list"
        for reviewer in project_reviewers:
            records = project_tasks.filtered(lambda x: x.reviewer_id.id == reviewer.id)
            ctx = {'tasks': records, 'url': project_url}
            mail_template.with_context(ctx).send_mail(records[0].id, force_send=True)
        for reviewer in nonproject_reviewers:
            records = nonproject_tasks.filtered(lambda x: x.reviewer_id.id == reviewer.id)
            ctx = {'tasks': records, 'url': nonproject_url}
            mail_template.with_context(ctx).send_mail(records[0].id, force_send=True)

    def _get_domain_task_evaluation(self):
        _domain = []
        user = self.env.user
        if self.env.user.has_group("base.group_system,ngsd_base.group_cbf"):
            return _domain
        if self.env.user.has_group("ngsd_base.group_cbf_hcm"):
            _domain = ["|", ('user_id', '=', user.id), ('user_id.employee_ids.en_area_id', '=', user.employee_id.en_area_id.id)]
            return _domain
        if self.env.user.has_group("base.group_user"):
            _domain = ["|", ('user_id', '=', user.id), ('reviewer_id', '=', user.id)]
            return _domain
        return _domain

    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        if self._context.get("ctx_task_evaluation_menu", False):
            _domain = self._get_domain_task_evaluation()
            if _domain:
                args.extend(_domain)
        return super()._name_search(name, args, operator, limit, name_get_uid)

    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        args = args or []
        if self._context.get("ctx_task_evaluation_menu", False):
            _domain = self._get_domain_task_evaluation()
            if _domain:
                args.extend(_domain)
        return super()._search(args, offset, limit, order, count, access_rights_uid)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        if self._context.get("ctx_task_evaluation_menu", False):
            _domain_extend = self._get_domain_task_evaluation()
            if _domain_extend:
                domain.extend(_domain_extend)
        return super().read_group(domain, fields, groupby, offset, limit, orderby, lazy)

    def action_lock(self):
        self = self.filtered(lambda x: not x.is_locked)
        self.write({"is_locked": True, "datetime_locked": fields.Datetime.now()})

    def action_unlock(self):
        self = self.filtered(lambda x: x.is_locked)
        self.write({"is_locked": False,
                    "datetime_locked": False,
                    "state": 'not_evaluated',
                    "date_confirm": False})

    @api.model
    def action_update_task_evaluation(self):
        self = self.sudo()
        today = fields.Date.Date.context_today(self)
        first_day_of_month = today.replace(day=1) + relativedelta(months=-1)
        employee_obj = self.env["hr.employee"]
        employee_obj.cron_generate_task_evaluation()
        task_evaluations = self.search([("date_evaluation", "=", str(first_day_of_month))])
        task_evaluations._compute_task_date()
        task_evaluations._compute_hour_actual()
