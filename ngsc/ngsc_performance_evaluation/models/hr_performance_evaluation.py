# -*- coding: utf-8 -*-
from datetime import datetime, time
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError, AccessError

from ..utils.constant import *
from ..utils.query import *

fields_options = [
    "employee_id", "work_email", "month", "year", "department_id",
    "number_of_tasks", "volume_point", "quality_point", "attitude_point",
    "evaluation_point", "rank", "state", "volume_evaluation",
    "quality_evaluation", "attitude_evaluation", "performance_evaluation",
    "approval_state", "note", "evaluation_task_ids", "hour_planned", "hour_actual",
    "direct_manager_id", "indirect_manager_id"
]


class HrPerformanceEvaluation(models.Model):
    _name = "ngsc.hr.performance.evaluation"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "date desc"
    _rec_name = "user_id"
    _description = "Đánh giá hiệu suất"

    name = fields.Char(string="Tên", default="Đánh giá hiệu suất cá nhân", tracking=True)
    employee_id = fields.Many2one("hr.employee", string="Nhân viên", required=True, tracking=True)
    user_id = fields.Many2one("res.users", string="Người dùng", related="employee_id.user_id")
    work_email = fields.Char(string="Email", related="employee_id.work_email", store=True, tracking=True)
    date = fields.Date(string="Thời gian", required=True, tracking=True)
    month = fields.Selection(string="Tháng đánh giá", selection=month_options, compute="_compute_date", store=True)
    year = fields.Selection([(str(num), str(num)) for num in
                             range(2020, int((datetime.now() + relativedelta(years=1)).strftime('%Y')))],
                            string="Năm đánh giá", compute="_compute_date", store=True)
    month_display = fields.Char(string="Tháng đánh giá", compute="_compute_date", store=True)
    en_block_id = fields.Many2one("en.name.block", string="Khối", tracking=True)
    department_id = fields.Many2one("hr.department", string="Trung tâm", tracking=True)
    en_department_id = fields.Many2one("en.department", string="Phòng ban", tracking=True)

    volume_evaluation = fields.Float(string="Đánh khối lượng", compute="_compute_volume_evaluation", store=True,
                                     help="Điểm khối lượng tính bằng: Tổng số timesheets được duyệt / Số số giờ làm việc chuẩn của tháng\n"
                                          "Trong đó:\n"
                                          "+ < 50%: Xếp hạng D \n"
                                          "+ >= 50%: 0 \n"
                                          "+ >= 60%: 0.4 \n"
                                          "+ >= 70%: 0.8 \n"
                                          "+ >= 80%: 1 \n"
                                          "+ >= 90%: 1.2 \n"
                                          "+ >= 100%: 1.4 \n"
                                          "+ >= 110%: 1.6 \n"
                                          "+ >= 120%: 1.8 + bonus (=< 0.2) "
                                          "+ Số giờ effort thực tế = Tổng số giờ user log trong dự án + Tổng số giờ user log ngoài dự án\n"
                                          "*Ngoài ra: Nếu vượt >110%, phần vượt được bonus tối đa +0.2 điểm ")
    volume_evaluation_display = fields.Char(string="Điểm khối lượng", compute="_compute_volume_evaluation",
                                            store=True)

    percentage_volume_evaluation = fields.Char(string="ĐTB khối lượng công việc", compute="_compute_volume_evaluation",
                                               store=True)

    quality_evaluation = fields.Float(string="Đánh giá chất lượng", compute="_compute_quality_evaluation", store=True,
                                      help="Điểm chất lượng tính bằng: Trung bình điểm đánh giá task trong tháng theo thang 1–5, trong đó:\n"
                                           "+ Cứ 0.1 điểm đánh giá >3 thì sẽ + 0.05 điểm quy đổi\n"
                                           "+ Cứ 0.1 điểm đánh giá <3 thì sẽ - 0.05 điểm quy đổi")
    quality_evaluation_display = fields.Char(string="Điểm chất lượng", compute="_compute_quality_evaluation",
                                             store=True)

    quality_evaluation_real = fields.Char(string="Điểm quy đổi của đánh giá chất lượng",
                                          compute="_compute_quality_evaluation",
                                          store=True)

    attitude_evaluation = fields.Selection(string="Đánh giá thái độ", selection=evaluation_options, tracking=True,
                                           help="Điểm thái độ được đánh giá theo tháng trên thang 1–5, với mốc chuẩn là 3 điểm tương ứng 0.5 điểm trên thang 1.0 ")
    attitude_evaluation_converted = fields.Float(string="Điểm đánh giá thái độ quy đổi",
                                                 compute="_compute_attitude_evaluation", store=True)
    attitude_evaluation_display = fields.Char(string="Điểm thái độ", compute="_compute_attitude_evaluation",
                                              store=True)

    attitude_evaluation_dqd = fields.Char(string="Điểm đánh giá thái độ Điểm quy đổi",
                                          compute="_compute_attitude_evaluation",
                                          store=True)

    performance_evaluation = fields.Float(string="Đánh giá hiệu suất", compute="_compute_performance_evaluation",
                                          store=True)
    rank = fields.Selection(string="Xếp loại", tracking=True, compute="_compute_rank", store=True,
                            selection=[('S', 'S'),
                                       ('A0', 'A+'),
                                       ('A1', 'A'),
                                       ('B', 'B'),
                                       ('C', 'C')],
                            help="S : ≥ 4.5 điểm\n"
                                 "A+ : Từ 3.5 đến < 4.5 điểm\n"
                                 "A : Từ 2.5 đến < 3.5 điểm\n"
                                 "B : Từ 1.5 đến < 2.5 điểm\n"
                                 "C : < 1.5 điểm (Nếu Tỉ lệ khối lượng < 50% hoặc điểm thái độ bằng 1 thì xếp hạng C")

    rank_display = fields.Char(string="Xếp loại trên báo cáo",
                               compute="_compute_rank",
                               store=True)

    state = fields.Selection(string="Trạng thái", tracking=True, default="new",
                             selection=[('new', 'Mới'),
                                        ('evaluated_again', 'Đánh giá lại'),
                                        ('to_approve', 'Chờ duyệt'),
                                        ('approved', 'Đã duyệt'),
                                        ('rejected', 'Từ chối')])
    approval_state = fields.Selection(string="Trạng thái duyệt", tracking=True, default="direct_manager",
                                      selection=[('direct_manager', 'CBQL trực tiếp'),
                                                 ('indirect_manager', 'CBQL gián tiếp'),
                                                 ('approved', 'Đã duyệt')])
    note = fields.Text(string="Ghi chú", tracking=True)
    evaluation_task_ids = fields.One2many("ngsc.hr.performance.evaluation.task", "performance_evaluation_id",
                                          string="Danh sách công việc đánh giá")
    number_of_tasks = fields.Integer(string="Số lượng công việc", compute="_compute_number_of_tasks", store=True)
    hour_planned = fields.Float(string="Số giờ dự kiến", compute="_compute_hour_planned", store=True)
    hour_actual = fields.Float(string="Số giờ thực hiện", compute="_compute_hour_timesheets", store=True)
    hour_daily_waiting_task_actual = fields.Float(string="Số giờ thực hiện cho daily_waiting hoặc task",
                                                  compute="_compute_hour_timesheets", store=True)
    hour_support_actual = fields.Float(string="Số giờ thực hiện cho support", compute="_compute_hour_timesheets",
                                       store=True)
    direct_manager_id = fields.Many2one("res.users", string="Quản lý trực tiếp", tracking=True)
    indirect_manager_id = fields.Many2one("res.users", string="Quản lý gián tiếp", tracking=True)
    is_direct_manager = fields.Boolean(string="Là quản lý trực tiếp", compute="_compute_check_manager")
    is_indirect_manager = fields.Boolean(string="Là quản lý gián tiếp", compute="_compute_check_manager")
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

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super().fields_get(allfields=allfields, attributes=attributes)
        for field_name, field_info in res.items():
            if field_name not in fields_options:
                field_info["selectable"] = False
                field_info["exportable"] = False
                field_info["searchable"] = False
                field_info["sortable"] = False
        return res

    @api.depends("date")
    def _compute_date(self):
        for rec in self:
            month = year = month_display = False
            if rec.date:
                month = f"{rec.date.month:02d}"
                year = str(rec.date.year)
                month_display = f"{month}-{year}"
            rec.month = month
            rec.year = year
            rec.month_display = month_display

    @api.depends("evaluation_task_ids")
    def _compute_number_of_tasks(self):
        for rec in self:
            rec.number_of_tasks = len(rec.evaluation_task_ids)

    @api.depends("employee_id")
    def _compute_hour_planned(self):
        for rec in self:
            rec.hour_planned = rec._get_hour_planned_employee_date_range()

    def _get_hour_planned_employee_date_range(self):
        first_day_of_month = self.date.replace(day=1)
        last_day_of_month = first_day_of_month + relativedelta(months=1, days=-1)
        start = datetime.combine(first_day_of_month, time.min)
        end = datetime.combine(last_day_of_month, time.max)
        technical_model_obj = self.env['en.technical.model'].sudo()
        technical_data = technical_model_obj.convert_daterange_to_data(self.employee_id, start, end)
        standard_hours = 0
        for line in technical_data:
            data = technical_data.get(line)
            if data and data.get('tech') not in ['off'] and data.get('tech_type') in ['leave', 'work']:
                standard_hours += data.get('number', 0)
        return standard_hours

    @api.depends("evaluation_task_ids", "evaluation_task_ids.hour_actual", "evaluation_task_ids.hour_actual_resource")
    def _compute_hour_timesheets(self):
        for rec in self:
            if rec.employee_id.department_id.activity_type == "delivery":
                rec.hour_actual = sum([x.hour_actual for x in rec.evaluation_task_ids.filtered(lambda x: x.project_id)])
                rec.hour_actual += sum([x.hour_actual_resource for x in rec.evaluation_task_ids.filtered(lambda x: not x.project_id)])
            else:
                rec.hour_actual = sum([x.hour_actual for x in rec.evaluation_task_ids])
            rec.hour_support_actual = sum([x.hour_actual for x in rec.evaluation_task_ids.filtered(lambda x: x.en_task_type == 'support')])
            rec.hour_daily_waiting_task_actual = sum([x.hour_actual for x in rec.evaluation_task_ids.filtered(lambda x: x.en_task_type in ['daily', 'waiting_task'])])

    @api.depends("employee_id", "hour_planned", "hour_actual")
    def _compute_volume_evaluation(self):
        for rec in self:
            volume_evaluation = 0
            volume_evaluation_display = "0 (0%)"
            percentage_volume_evaluation = "0%"
            if rec.hour_planned > 0:
                effort_ratio = rec.hour_actual / rec.hour_planned
                percentage = round(effort_ratio * 100)
                percentage_volume_evaluation = f"{percentage}%"
                base_point = 0
                if percentage < 50:
                    base_point = 0
                elif percentage >= 120:
                    base_point = 1.8
                elif percentage >= 110:
                    base_point = 1.6
                elif percentage >= 100:
                    base_point = 1.4
                elif percentage >= 90:
                    base_point = 1.2
                elif percentage >= 80:
                    base_point = 1.0
                elif percentage >= 70:
                    base_point = 0.8
                elif percentage >= 60:
                    base_point = 0.5
                elif percentage >= 50:
                    base_point = 0.1
                # Tính bonus nếu effort_ratio > 1.2 (tức là >120%)
                if effort_ratio > 1.2:
                    bonus = min((effort_ratio - 1.2) * 0.1, 0.2)
                    volume_evaluation = base_point + bonus
                else:
                    volume_evaluation = base_point
                volume_evaluation = volume_evaluation if volume_evaluation >=0 else 0
                volume_evaluation_display = f"{round(volume_evaluation, 2)} ({percentage}%)"
            rec.volume_evaluation = volume_evaluation
            rec.volume_evaluation_display = volume_evaluation_display
            rec.percentage_volume_evaluation = percentage_volume_evaluation

    @api.depends("employee_id", "evaluation_task_ids", "evaluation_task_ids.evaluation")
    def _compute_quality_evaluation(self):
        for rec in self:
            evaluations = [float(x.evaluation) for x in rec.evaluation_task_ids if x.evaluation]
            if not evaluations:
                rec.quality_evaluation = 0.0
                rec.quality_evaluation_display = ""
                rec.quality_evaluation_real = ""
                continue
            avg = round(sum(evaluations) / len(rec.evaluation_task_ids), 2)
            value = 1
            delta = avg - 3.0
            step = int(abs(delta) / 0.1)
            if delta > 0:
                value += 0.05 * step
            elif delta < 0:
                value -= 0.05 * step
            final_score = round(value, 2) if value >= 0 else 0
            display_final = int(final_score) if final_score == int(final_score) else final_score
            display_avg = int(avg) if avg == int(avg) else avg
            display_text = f"{display_final} ({display_avg})"
            rec.quality_evaluation = final_score
            rec.quality_evaluation_display = display_text
            rec.quality_evaluation_real = str(display_avg)

    @api.depends("employee_id", "attitude_evaluation")
    def _compute_attitude_evaluation(self):
        for rec in self:
            if not rec.attitude_evaluation:
                rec.attitude_evaluation_display = ""
                rec.attitude_evaluation_converted = 0.0
                rec.attitude_evaluation_dqd = ""
                continue
            score = int(rec.attitude_evaluation)
            if score >= 3:
                score_converted = 0.5 + (score - 3) * 0.25
            else:
                score_converted = 0.5 - (3 - score) * 0.15
            if score == 1:
                score_converted = 0
            rec.attitude_evaluation_converted = round(score_converted, 2) if score_converted >= 0 else 0
            display_score = int(score_converted) if score_converted == int(score_converted) else score_converted
            rec.attitude_evaluation_display = f"{display_score} ({score})"
            rec.attitude_evaluation_dqd = f"{display_score}"

    @api.depends("volume_evaluation", "quality_evaluation", "attitude_evaluation_converted")
    def _compute_performance_evaluation(self):
        for rec in self:
            total = sum([rec.volume_evaluation, rec.quality_evaluation, rec.attitude_evaluation_converted])
            rec.performance_evaluation = round(total, 2)

    @api.depends("attitude_evaluation", "performance_evaluation", "hour_actual", "hour_planned")
    def _compute_rank(self):
        for rec in self:
            if rec.attitude_evaluation == "1":
                rec.rank = "C"
                rec.rank_display = "C"
                continue
            if not rec.performance_evaluation:
                rec.rank = False
                rec.rank_display = ""
                continue
            effort_ratio = rec.hour_actual / rec.hour_planned if rec.hour_planned > 0 else 0.0
            percentage = round(effort_ratio * 100)
            if percentage < 50:
                rec.rank = "C"
                rec.rank_display = "C"
                continue
            score = rec.performance_evaluation
            if score >= 4.5:
                rec.rank = "S"
                rec.rank_display = "S"
            elif 3.5 <= score < 4.5:
                rec.rank = "A0"
                rec.rank_display = "A+"
            elif 2.5 <= score < 3.5:
                rec.rank = "A1"
                rec.rank_display = "A"
            elif 1.5 <= score < 2.5:
                rec.rank = "B"
                rec.rank_display = "B"
            elif score < 1.5:
                rec.rank = "C"
                rec.rank_display = "C"

    def _compute_check_manager(self):
        user = self.env.user
        for rec in self:
            rec.is_direct_manager = rec.direct_manager_id == user
            rec.is_indirect_manager = rec.indirect_manager_id == user

    def action_to_approve(self):
        states = list(set(self.mapped("state")))
        not_attitude_evaluations = self.filtered(lambda x: not x.attitude_evaluation)
        if len(states) > 1 or ("new" not in states and "rejected" not in states):
            raise ValidationError("Vui lòng chọn danh sách các đánh giá hiệu suất có cùng trạng thái Mới.")
        if not_attitude_evaluations:
            raise ValidationError("Vui lòng nhập Điểm đánh giá thái độ trước khi Gửi duyệt.")
        for rec in self:
            if not rec.indirect_manager_id:
                raise UserError(
                    "Bạn không thể gửi duyệt vì nhân viên chưa được thiết lập Quản lý gián tiếp. Vui lòng cập nhật lại thông tin nhân sự.")
            if not rec.is_direct_manager:
                raise UserError("Chỉ quản lý trực tiếp của nhân viên mới có quyền gửi duyệt.")
            rec.write({"state": "to_approve", "approval_state": "indirect_manager"})

    def action_again_approve(self):
        states = list(set(self.mapped("state")))
        if self.approval_state == 'indirect_manager':
            if len(states) > 1 or ("to_approve" not in states):
                raise ValidationError("Vui lòng chọn danh sách các đánh giá hiệu suất có cùng trạng thái Chờ duyệt.")
            for rec in self:
                if not rec.is_indirect_manager:
                    raise UserError("Chỉ quản lý Gián tiếp của nhân viên mới có quyền từ chối.")
                rec.write({"state": "evaluated_again", "approval_state": "direct_manager"})
                task_evaluation_ids = self.env['task.evaluation'].search([
                    ('employee_id', '=', rec.employee_id.id),
                    ('month_evaluation', '=', rec.month_display)
                ])
                for task in task_evaluation_ids:
                    task.write({"state": "evaluated_again", "is_locked": False})

        else:
            if len(states) > 1 or ("new" not in states and "rejected" not in states):
                raise ValidationError("Vui lòng chọn danh sách các đánh giá hiệu suất có cùng trạng thái Mới.")
            for rec in self:
                if not rec.is_direct_manager:
                    raise UserError("Chỉ quản lý Trực tiếp của nhân viên mới có quyền từ chối.")
                rec.write({"state": "evaluated_again"})
                rec.evaluation_task_ids.mapped("task_evaluation_id").write({"state": "evaluated_again", "is_locked": False})

    def action_approve(self):
        states = list(set(self.mapped("state")))
        if len(states) > 1 or "to_approve" not in states:
            raise ValidationError("Vui lòng chọn danh sách các đánh giá hiệu suất có cùng trạng thái Chờ duyệt")
        for rec in self:
            if not rec.is_indirect_manager:
                raise UserError("Chỉ quản lý gián tiếp của nhân viên mới có quyền phê duyệt.")
            rec.write({"state": "approved", "approval_state": "approved"})

    # def action_reject(self):
    #     states = list(set(self.mapped("state")))
    #     if len(states) > 1 or "to_approve" not in states:
    #         raise ValidationError("Vui lòng chọn danh sách các đánh giá hiệu suất có cùng trạng thái Chờ duyệt")
    #     for rec in self:
    #         if not rec.is_indirect_manager:
    #             raise UserError("Chỉ quản lý gián tiếp của nhân viên mới có quyền từ chối.")
    #         rec.write({"state": "rejected", "approval_state": "direct_manager"})

    @api.model
    def cron_remind_direct_manager_performance_evaluation(self, date=False):
        if date:
            evaluation_date = fields.Date.from_string(date)
        else:
            evaluation_date = fields.Date.Date.context_today(self)
        first_day_of_month = evaluation_date.replace(day=1) + relativedelta(months=-1)

        _domain = [("approval_state", "=", "direct_manager"),
                   ("date", "=", first_day_of_month)]
        performance_evaluations = self.env["ngsc.hr.performance.evaluation"].sudo().search(_domain)
        direct_manager_ids = performance_evaluations.mapped("direct_manager_id")
        mail_template = self.env.ref('ngsc_performance_evaluation.task_evaluation_remind_manager_mail_template')
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        action = self.env.ref('ngsc_performance_evaluation.hr_performance_evaluation_act_window')
        url = f"{base_url}/web#action={action.id}&model=ngsc.hr.performance.evaluation&view_type=list"
        for manager in direct_manager_ids[:2]:
            records = performance_evaluations.filtered(lambda x: x.direct_manager_id.id == manager.id)
            ctx = {
                'manager_name': manager.name,
                'manager_email': manager.email,
                'evaluations': records,
                'url': url}
            mail_template.with_context(ctx).send_mail(records[0].id, force_send=True)

    @api.model
    def cron_remind_indirect_manager_performance_evaluation(self, date=False):
        if date:
            evaluation_date = fields.Date.from_string(date)
        else:
            evaluation_date = fields.Date.Date.context_today(self)
        first_day_of_month = evaluation_date.replace(day=1) + relativedelta(months=-1)

        _domain = [("approval_state", "=", "indirect_manager"),
                   ("date", "=", first_day_of_month)]
        performance_evaluations = self.env["ngsc.hr.performance.evaluation"].sudo().search(_domain)
        indirect_manager_ids = performance_evaluations.mapped("indirect_manager_id")
        mail_template = self.env.ref('ngsc_performance_evaluation.task_evaluation_remind_manager_mail_template')
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        action = self.env.ref('ngsc_performance_evaluation.hr_performance_evaluation_act_window')
        url = f"{base_url}/web#action={action.id}&model=ngsc.hr.performance.evaluation&view_type=list"
        for manager in indirect_manager_ids[:2]:
            records = performance_evaluations.filtered(lambda x: x.indirect_manager_id.id == manager.id)
            ctx = {
                'manager_name': manager.name,
                'manager_email': manager.email,
                'evaluations': records,
                'url': url
            }
            mail_template.with_context(ctx).send_mail(records[0].id, force_send=True)

    def action_open_record(self):
        return self.open_form_or_tree_view('ngsc_performance_evaluation.hr_performance_evaluation_act_window',
                                           'ngsc_performance_evaluation.hr_performance_evaluation_view_form', self)

    def action_update_data(self):
        self = self.sudo()
        first_day_of_month = fields.Date.Date.context_today(self).replace(day=1) + relativedelta(months=-1)
        if self.filtered(lambda x: str(x.date) != str(first_day_of_month)):
            raise ValidationError(f"Chỉ cập nhật được danh sách đánh giá tháng {first_day_of_month.strftime('%m/%Y')}.")
        states = set(self.mapped("state"))
        if len(states) > 1 or not states.intersection({"new", "rejected"}):
            raise ValidationError("Vui lòng chọn danh sách các đánh giá hiệu suất có cùng trạng thái Mới.")
        attitude_old_map = {r.employee_id.id: r.attitude_evaluation for r in self if r.attitude_evaluation}
        self.unlink()
        result = self.env["hr.employee"].cron_generate_hr_performance_evaluation()
        if attitude_old_map:
            result.filtered(lambda r: r.employee_id.id in attitude_old_map)
            for rec in result:
                val = attitude_old_map.get(rec.employee_id.id)
                if not val:
                    continue
                rec.attitude_evaluation = val
        self.env.user.notify_success("Cập nhật dữ liệu đánh giá hiệu suất thành công.")

    @api.model
    def action_update_performance_evaluation(self):
        self = self.sudo()
        today = fields.Date.Date.context_today(self)
        first_day_of_month = today.replace(day=1) + relativedelta(months=-1)
        evaluation_obj = self.env["ngsc.hr.performance.evaluation"].sudo()
        task_evaluation_obj = self.env["task.evaluation"].sudo()
        self.env["ngsc.hr.performance.evaluation.task"].sudo().search([("performance_evaluation_id.date", "=", first_day_of_month)]).unlink()
        records = evaluation_obj.search([("date", "=", first_day_of_month)])

        for r in records:
            evaluation_task_ids = []
            _domain_project = [("user_id", "=", r.employee_id.user_id.id),
                               ("project_task_id", "!=", False),
                               ("project_task_id.category", "=", "task"),
                               ("project_task_id.stage_id.en_mark", "!=", "b"),
                               ("project_task_id.project_wbs_state", "=", "approved"),
                               ("date_evaluation", "=", first_day_of_month), ("is_locked", "=", True), ("state", "=", 'evaluated')]
            _domain_nonproject = [("user_id", "=", r.employee_id.user_id.id),
                                  ("nonproject_task_id", "!=", False),
                                  ("date_evaluation", "=", first_day_of_month), ("is_locked", "=", True),
                                  ("state", "=", 'evaluated')]
            project_tasks = task_evaluation_obj.search(_domain_project)
            nonproject_tasks = task_evaluation_obj.search(_domain_nonproject)
            evaluation_task_ids = [(0, 0, {"task_evaluation_id": line.id}) for line in project_tasks]
            evaluation_task_ids += [(0, 0, {"task_evaluation_id": line.id}) for line in nonproject_tasks]
            r.write({"evaluation_task_ids": evaluation_task_ids})

        # employee_obj = self.env["hr.employee"].sudo()
        # task_evaluation_obj = self.env["task.evaluation"].sudo()
        # evaluation_obj = self.env["ngsc.hr.performance.evaluation"].sudo()
        # task_performance_obj = self.env["ngsc.hr.performance.evaluation.task"].sudo()
        # employee_obj.with_context(refresh=True).cron_generate_hr_performance_evaluation()
        # performance_evaluations = evaluation_obj.search([("date", "=", str(first_day_of_month))])
        # task_evaluations_exists = performance_evaluations.mapped("evaluation_task_ids.task_evaluation_id")
        # miss_task_evaluations = task_evaluation_obj.search([("date_evaluation", "=", str(first_day_of_month)),
        #                                                     ("is_locked", "=", True),
        #                                                     ("state", "=", 'evaluated'),
        #                                                     ("id", "not in", task_evaluations_exists.ids)])
        # miss_users = miss_task_evaluations.mapped("user_id")
        # performance_evaluation_update = performance_evaluations.filtered(lambda x: x.user_id in miss_users)
        # for record in performance_evaluation_update:
        #     task_miss = miss_task_evaluations.filtered(lambda x: x.user_id == record.user_id)
        #     values = [{
        #         "performance_evaluation_id": record.id,
        #         "task_evaluation_id": line.id}
        #         for line in task_miss]
        #     task_performance_obj.create(values)
        #     if task_miss.project_task_id.task_old_related_id:
        #         task_performance_obj.search([("performance_evaluation_id", "=", record.id),
        #                                      ("task_id", "=", task_miss.project_task_id.task_old_related_id.id)]).unlink()
        # performance_evaluations.mapped("evaluation_task_ids")._compute_task_evaluation()
