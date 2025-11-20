from odoo import models, fields, api, _
from odoo.tools.misc import format_date, DEFAULT_SERVER_DATE_FORMAT
from datetime import timedelta, datetime, time
from odoo.tools import config, date_utils, get_lang, html2plaintext
from dateutil.relativedelta import relativedelta
from decimal import localcontext, Decimal, ROUND_HALF_UP
from pytz import timezone
import math
from collections import defaultdict


class ProjectStatusReport(models.Model):
    _name = "project.status.report"
    _description = "Báo cáo tuần"

    user_id = fields.Many2one('res.users')
    project_en_code = fields.Char(string='Mã dự án')
    project_id = fields.Many2one('project.project', string='Tên dự án')
    project_en_area_id = fields.Many2one(string='Khu vực', comodel_name='en.name.area')
    project_en_department_id = fields.Many2one(string='Trung tâm', comodel_name='hr.department')
    project_user_id = fields.Many2one('res.users', string='PM')
    project_en_project_qa_id = fields.Many2one('res.users', string='QA')
    project_en_project_sale_id = fields.Many2one('res.users', string='Sales')
    project_en_project_type_id = fields.Many2one(string='Loại dự án', comodel_name='en.project.type')
    project_description = fields.Html(string='Phạm vi')
    project_date_start = fields.Date(string='Ngày bắt đầu')
    project_first_date = fields.Date(string='Ngày kết thúc')
    project_date = fields.Date(string='Ngày cuối cùng')
    project_stage_id = fields.Many2one('project.project.stage', string='Trạng thái')

    # in_week_task = fields.Text(string='Công việc hoàn thành trong tuần', compute='_get_missing_data', store=True)
    # plan_task = fields.Text(string='Kế hoạch 2 tuần tiếp theo', compute='_get_missing_data', store=True)
    task_plan_week = fields.Html(string='Công việc & Kế hoạch', compute='_get_missing_data', store=True)
    risk = fields.Html(string='Rủi ro/ cơ hội', compute='_get_missing_data', store=True)
    problem = fields.Html(string='Vấn đề', compute='_get_missing_data', store=True)
    document = fields.Html(string='Sản phẩm bàn giao', compute='_get_missing_data', store=True)
    qa_evaluate = fields.Html('Đánh giá của QA', compute='_get_missing_data', store=True)
    wbs_plan = fields.Float(string='Kế hoạch (WBS)', compute='_get_missing_data', store=True)
    wbs_indate = fields.Float(string='Thực tế (WBS)', compute='_get_missing_data', store=True)
    wbs_rate = fields.Float(string='% Tiến độ', compute='_get_missing_data', store=True)

    resource_bmm = fields.Float(string='BMM', compute='_get_missing_data', store=True)
    resource_plan = fields.Float(string='Plan', compute='_get_missing_data', store=True)
    resource_mm_actual = fields.Float(string='MM actual', compute='_get_missing_data', store=True)
    resource_rate = fields.Float(string='%(MM actual/Plan)', compute='_get_missing_data', store=True)

    response_rate_plan = fields.Float(string='Cam kết % SLA phản hồi')
    response_rate = fields.Float(string='%SLA phản hồi')
    response_ticket = fields.Integer(string='Tổng Ticket đúng hạn phản hồi')
    response_ticket_to_date = fields.Integer(string='Tổng Ticket đến hạn phản hồi')
    count_ticket = fields.Integer('Số ticket')

    handle_rate_plan = fields.Float(string='Cam kết % SLA xử lý')
    handle_rate = fields.Float(string='% SLA xử lý')
    handle_ticket = fields.Integer(string='Tổng Ticket đúng hạn xử lý')
    handle_ticket_to_date = fields.Integer(string='Tổng Ticket đến hạn xử lý')
    note = fields.Html(string='Ghi chú')

    @api.depends('project_id')
    def _get_missing_data(self):
        self = self.sudo()
        for rec in self:
            date_from, date_to = self._get_date_range()
            date_end_month = date_to + relativedelta(day=1, months=1, days=-1)
            # WBS
            wbs_id = rec.project_id.en_current_version

            wbs_plan = wbs_id.planned_hours
            rec.wbs_plan = wbs_plan

            wbs_indate = wbs_id.effective_hours
            rec.wbs_indate = wbs_indate

            rec.wbs_rate = (wbs_indate / wbs_plan) * 100 if wbs_plan else 0

            # Resource
            resource_bmm = sum(rec.project_id.en_bmm_ids.filtered(lambda x: x.date <= date_end_month).mapped('bmm'))
            rec.resource_bmm = resource_bmm
            resource_plan = 0
            for line in rec.project_id.en_resource_id.order_line:
                if line.date_start > date_end_month:
                    continue
                employee = line.employee_id
                start_plan = line.date_start
                end_plan = min(line.date_end, date_end_month)
                for date_step in date_utils.date_range(datetime.combine(start_plan + relativedelta(day=1), time.min), datetime.combine(end_plan + relativedelta(day=1, months=1, days=-1), time.max), relativedelta(months=1)):
                    compared_from = (date_step + relativedelta(day=1)).date()
                    compared_to = (date_step + relativedelta(months=1, day=1, days=-1)).date()
                    y = rec.project_id.mm_rate
                    x = self.env['en.technical.model'].convert_daterange_to_hours(employee, max(start_plan, compared_from), min(compared_to, end_plan)) * line.workload / 8
                    resource_plan += x / y if y else 0
            resource_plan += sum(rec.project_id.en_history_resource_ids.filtered(lambda x: (int(x.month) <= date_to.month and int(x.year) == date_to.year) or int(x.year) < date_to.year).mapped('plan'))
            rec.resource_plan = resource_plan
            total_ts = 0
            for ts in rec.project_id.timesheet_ids.filtered(lambda x: x.date <= date_to):
                if ts.en_state == 'approved':
                    total_ts += ts.unit_amount
                if ts.ot_state == 'approved':
                    total_ts += ts.ot_time
            if rec.project_id.mm_rate != 0:
                total = (total_ts / 8) / rec.project_id.mm_rate
            else:
                total = (total_ts / 8)
            total += sum(rec.project_id.en_history_resource_ids.filtered(lambda x: (int(x.month) <= date_to.month and int(x.year) == date_to.year) or int(x.year) < date_to.year).mapped('actual'))
            rec.resource_mm_actual = total

            rec.resource_rate = (total / resource_plan) * 100 if resource_plan else 0

            task_lines = rec.project_id.en_work_plans_ids.filtered(lambda w: w.date_work_plan and date_from <= w.date_work_plan <= date_to)

            risks = rec.project_id.en_risk_ids.filtered(lambda r: r.stage_id.name not in ['Hủy', 'Đóng', 'Đã đóng'])
            tmpl = """
                <tr class="o_data_row">
                    <td class="o_data_cell o_field_cell o_list_text">%s</td>
                    <td class="o_data_cell o_field_cell o_list_text">%s</td>
                </tr>"""

            tmpl1 = """
                <tr class="o_data_row">
                    <td class="o_data_cell o_field_cell o_list_text text-center">%s</td>
                    <td class="o_data_cell o_field_cell o_list_text text-center">%s</td>
                    <td class="o_data_cell o_field_cell o_list_text">%s</td>
                    <td class="o_data_cell o_field_cell o_list_text">%s</td>
                </tr>"""

            tmpl2 = """
                <tr class="o_data_row">
                    <td class="o_data_cell o_field_cell o_list_text">%s</td>
                    <td class="o_data_cell o_field_cell o_list_text">%s</td>
                    <td class="o_data_cell o_field_cell o_list_text">%s</td>
                </tr>"""

            task_line = f"""
                <table style="width: 100%;">
                    <tbody>
                        <tr class="o_data_row" style="background-color: #d8d8d8;">
                            <td class="o_data_cell o_field_cell o_list_text"><strong>Ngày</strong></td>
                            <td class="o_data_cell o_field_cell o_list_text"><strong>Công việc hoàn thành trong tuần</strong></td>
                            <td class="o_data_cell o_field_cell o_list_text"><strong>Kế hoạch 2 tuần tiếp theo</strong></td>
                        </tr>
                        {''.join([tmpl2%(task.date_work_plan.strftime('%d/%m/%Y') if task.date_work_plan else '', task.work_done or '', task.plan_done or '') for task in task_lines])}
                    </tbody>
                </table>
            """

            rec.task_plan_week = task_line if task_lines else ''
            
            risk = f"""
            <table style="width: 100%;">
                <tbody>
                    <tr class="o_data_row" style="background-color: #d8d8d8;">
                        <td class="o_data_cell o_field_cell o_list_text"><strong>Rủi ro/ cơ hội</strong></td>
                        <td class="o_data_cell o_field_cell o_list_text"><strong>Biện pháp khắc phục</strong></td>
                    </tr>
                    {''.join([tmpl%(r.name or '', r.recover or '') for r in risks])}
                </tbody>
            </table>
                        """
#             risk_name = '\n'.join(['- ' + r.name for r in risks if r.name])
#             risk_recover = '\n'.join([r.recover for r in risks if r.recover])
#             risk = f"""*Rủi ro/ cơ hội :
# {risk_name}
# *Biện pháp khắc phục
# {risk_recover}"""
#             rec.risk = risk if risks else ''
            rec.risk = risk if risks else ''

            problems = rec.project_id.en_problem_ids.filtered(lambda r: r.stage_id.name not in ['Bàn giao', 'Hủy', 'Hoàn thành', 'Đóng', 'Đã đóng'])

#             problem_name = '\n'.join(['- ' + r.name for r in problems if r.name])
#             problem_solution_plan = '\n'.join([r.solution_plan for r in problems if r.solution_plan])
#             problem = f"""
# *Các vấn đề:
# {problem_name}
# *Phương án giải quyết
# {problem_solution_plan}
#             """
            problem = f"""
            <table style="width: 100%;">
                <tbody>
                    <tr class="o_data_row" style="background-color: #d8d8d8;">
                        <td class="o_data_cell o_field_cell o_list_text"><strong>Các vấn đề</strong></td>
                        <td class="o_data_cell o_field_cell o_list_text"><strong>Phương án giải quyết</strong></td>
                    </tr>
                    {''.join([tmpl%(p.name or '', p.solution_plan or '') for p in problems])}
                </tbody>
            </table>
            """
            rec.problem = problem if problems else ''
            checkbox = 'x'
            documents = rec.project_id.en_document_ids.filtered(
                lambda d: ((d.en_project_milestone or d.en_payment_milestone) and d.handover_date and date_from <= d.handover_date <= date_to)
                or (d.state == 'new' and d.handover_date and (d.handover_date < date_from or d.handover_date <= date_to + relativedelta(days=30)))
            )
            document = f"""
                <table style="width: 100%;">
                    <tbody>
                        <tr class="o_data_row" style="background-color: #d8d8d8;">
                            <td class="o_data_cell o_field_cell o_list_text"><strong>Mốc dự án</strong></td>
                            <td class="o_data_cell o_field_cell o_list_text"><strong>Mốc thanh toán</strong></td>
                            <td class="o_data_cell o_field_cell o_list_text"><strong>Hoàn thành dự kiến</strong></td>
                            <td class="o_data_cell o_field_cell o_list_text"><strong>Sản phẩm bàn giao</strong></td>
                        </tr>
                        {''.join([tmpl1%(checkbox if doc.en_project_milestone else '' , checkbox if doc.en_payment_milestone else '', doc.handover_date.strftime('%d/%m/%Y') if doc.handover_date else '', doc.name or '') for doc in documents])}
                    </tbody>
                </table>
            """

            rec.document = document if documents else ''

            qa_evaluates = rec.project_id.en_qa_evaluate_ids.filtered(lambda q: q.date and date_from <= q.date <= date_to)
            qa_evaluate = f"""
                <table style="width: 100%;">
                    <tbody>
                        <tr class="o_data_row" style="background-color: #d8d8d8;">
                            <td class="o_data_cell o_field_cell o_list_text"><strong>Ngày tạo</strong></td>
                            <td class="o_data_cell o_field_cell o_list_text"><strong>Mô tả</strong></td>
                        </tr>
                        {''.join([tmpl%(qa.date.strftime('%d/%m/%Y') if qa.date else '', qa.qa_valuate or '') for qa in qa_evaluates])}
                    </tbody>
                </table>
            """
            rec.qa_evaluate = qa_evaluate if qa_evaluates else ''

            rec.count_ticket = self.env['helpdesk.ticket'].search_count([('project_id', '=', rec.project_id.id)])

    @api.model
    def get_total_data(self, domain):
        datas = self.read_group(domain=domain, fields=['project_hours', 'standard_hours', 'leave_hours', 'other_nonproject_hours', 'kd_nonproject_hours'], groupby=['user_id'])
        data = datas and datas[0] or {}
        project_hours = data.get('project_hours') or 0
        standard_hours = data.get('standard_hours') or 0
        leave_hours = data.get('leave_hours') or 0
        kd_nonproject_hours = data.get('kd_nonproject_hours') or 0
        other_nonproject_hours = data.get('other_nonproject_hours') or 0

        if not (standard_hours - leave_hours):
            return {'project_rate': 0, 'other_rate': 0, 'kd_rate': 0, 'all_rate': 0}
        return {
            'project_rate': project_hours / (standard_hours - leave_hours) * 100,
            'other_rate': other_nonproject_hours / (standard_hours - leave_hours) * 100,
            'kd_rate': kd_nonproject_hours / (standard_hours - leave_hours) * 100,
            'all_rate': (project_hours + other_nonproject_hours + kd_nonproject_hours) / (standard_hours - leave_hours) * 100,
        }

    def _get_date_range(self):
        date_from_txt = self._context.get('date_from') or fields.Date.Date.Date.context_today(self)
        date_to_txt = self._context.get('date_to') or fields.Date.Date.Date.context_today(self)
        date_from = min(fields.Date.from_string(date_from_txt), fields.Date.from_string(date_to_txt))
        date_to = max(fields.Date.from_string(date_from_txt), fields.Date.from_string(date_to_txt))
        return date_from, date_to

    def init_data(self):
        if self.env.user.has_group('ngsd_base.group_td'):
            self = self.sudo()
        date_from, date_to = self._get_date_range()
        date_from_time = date_from - relativedelta(hours=7)
        date_to_time = date_to - relativedelta(hours=7) + relativedelta(days=1)
        today = (fields.Date.Date.Date.context_today(self) + relativedelta(days=1, hours=-7)).strftime('%Y-%m-%d %H:%M:%S')
        ctx = self._context
        en_area_ids = ctx.get('en_area_ids')
        en_department_ids = ctx.get('en_department_ids')
        project_ids = ctx.get('project_ids')
        domain = [('stage_id.en_state', 'in', ['draft', 'doing', 'wait_for_execution'])]
        if en_area_ids:
            domain += [('en_area_id', 'in', en_area_ids)]
        if en_department_ids:
            domain += [('en_department_id', 'in', en_department_ids)]
        if project_ids:
            domain += [('id', 'in', project_ids)]
        project = self.env['project.project'].search(domain)

        project_txt = 'and pp.id in %s' % str(project.ids).replace('[', '(').replace(']', ')') if project else 'and pp.id < 0'

        query = f"""
            DELETE FROM {self._table} WHERE user_id = {self.env.user.id};
            with 
            rep AS (
                select project_id,
                    sum(case when coalesce(en_day_rep, CURRENT_DATE) <= en_dl_rep then 1 else 0 end) has_valid,
                    count(*) total,
                    sum(case when coalesce(en_day_rep, CURRENT_DATE) <= en_dl_rep then 1 else 0 end)::numeric / count(*) as rate
                from helpdesk_ticket
                join helpdesk_stage on helpdesk_ticket.stage_id = helpdesk_stage.id
                join helpdesk_ticket_type on helpdesk_ticket.ticket_type_id = helpdesk_ticket_type.id
                where helpdesk_stage.en_state != 'cancel'
                and helpdesk_ticket_type.name != 'CR'
                {f"and en_dl_rep >= '{date_from_time.strftime('''%Y-%m-%d %H:%M:%S''')}'" if date_from else ''}
                {f"and en_dl_rep <= '{date_to_time.strftime('''%Y-%m-%d %H:%M:%S''')}'" if date_to_time else ''}
                {f"and en_dl_rep <= '{today}'"}
                group by project_id
            ),
            com AS (
                select project_id,
                    sum(case when coalesce(en_day_com, CURRENT_DATE) <= en_dl then 1 else 0 end) has_valid,
                    count(*) total,
                    sum(case when coalesce(en_day_com, CURRENT_DATE) <= en_dl then 1 else 0 end)::numeric / count(*) as rate 
                from helpdesk_ticket 
                join helpdesk_stage on helpdesk_ticket.stage_id = helpdesk_stage.id
                join helpdesk_ticket_type on helpdesk_ticket.ticket_type_id = helpdesk_ticket_type.id
                where helpdesk_stage.en_state != 'cancel'
                and helpdesk_ticket_type.name != 'CR'
                {f"and en_dl >= '{date_from_time.strftime('''%Y-%m-%d %H:%M:%S''')}'" if date_from_time else ''}
                {f"and en_dl <= '{date_to_time.strftime('''%Y-%m-%d %H:%M:%S''')}'" if date_to_time else ''}
                {f"and en_dl <= '{today}'"}
                group by project_id
            ),
            rep_project AS (
                select project_id,
                    sum(total_ticket_ontime_feedback) has_valid_rep,
                    sum(total_ticket_due_feedback) total_rep,
                    case when sum(total_ticket_due_feedback) != 0 then sum(total_ticket_ontime_feedback)::numeric/sum(total_ticket_due_feedback) else 0 end rate_rep,
                    sum(total_ticket_ontime_process) has_valid_com,
                    sum(total_ticket_due_process) total_com,
                    case when sum(total_ticket_due_process) != 0 then sum(total_ticket_ontime_process)::numeric/sum(total_ticket_due_process) else 0 end rate_com
                from en_work_plans
                where 1=1
                {f"and date_work_plan >= '{date_from.strftime('''%Y-%m-%d''')}'" if date_from else ''}
                {f"and date_work_plan <= '{date_to.strftime('''%Y-%m-%d''')}'" if date_to else ''}
                {f"and date_work_plan <= '{today}'"}
                group by project_id
            ),
            com_plan_id AS (
                select project_id, max(id) id
                from en_processing_rate
                where 1=1
                {f"and end_date >= '{date_from.strftime('''%Y-%m-%d''')}'" if date_from else ''}
                {f"and start_date <= '{date_to.strftime('''%Y-%m-%d''')}'" if date_to else ''}
                group by project_id
            ),
            com_plan AS (
                select en_processing_rate.project_id, rate
                from en_processing_rate
                join com_plan_id on com_plan_id.id = en_processing_rate.id
            ),
            
            rep_plan_id AS (
                select project_id, max(id) id
                from en_response_rate
                where 1=1
                {f"and end_date >= '{date_from.strftime('''%Y-%m-%d''')}'" if date_from else ''}
                {f"and start_date <= '{date_to.strftime('''%Y-%m-%d''')}'" if date_to else ''}
                group by project_id
            ),
            rep_plan AS (
                select en_response_rate.project_id, rate
                from en_response_rate
                join rep_plan_id on rep_plan_id.id = en_response_rate.id
            )
            
            INSERT INTO {self._table} (project_en_code, project_id, project_en_area_id, project_en_department_id, project_user_id, project_en_project_qa_id, project_en_project_sale_id, project_en_project_type_id, project_description, project_date_start, project_first_date, project_date, project_stage_id, response_rate_plan, response_rate, response_ticket, response_ticket_to_date, handle_rate_plan, handle_rate, handle_ticket, handle_ticket_to_date, user_id)
            select
                pp.en_code project_en_code,
                pp.id project_id,
                pp.en_area_id project_en_area_id,
                pp.en_department_id project_en_department_id,
                pp.user_id project_user_id,
                pp.en_project_qa_id project_en_project_qa_id,
                pp.en_project_sale_id project_en_project_sale_id,
                pp.en_project_type_id project_en_project_type_id,
                pp.description project_description,
                pp.date_start project_date_start,
                pp.first_date project_first_date,
                pp.date project_date,
                pp.stage_id project_stage_id,
                rep_plan.rate*100 response_rate_plan,
                (case when rep.total > 0 then rep.rate else rep_project.rate_rep end)*100 as response_rate,
                case when rep.total > 0 then rep.has_valid else rep_project.has_valid_rep end as response_ticket,
                case when rep.total > 0 then rep.total else rep_project.total_rep end as response_ticket_to_date,
                com_plan.rate*100 handle_rate_plan,
                (case when com.total > 0 then com.rate else rep_project.rate_com end)*100 as handle_rate,
                case when com.total > 0 then com.has_valid else rep_project.has_valid_com end as handle_ticket,
                case when com.total > 0 then com.total else rep_project.total_com end as handle_ticket_to_date,
                {self.env.user.id}
            from project_project pp
            left join com on com.project_id = pp.id
            left join rep on rep.project_id = pp.id
            left join com_plan on com_plan.project_id = pp.id
            left join rep_plan on rep_plan.project_id = pp.id
            left join rep_project on rep_project.project_id = pp.id
            where 1=1
            {project_txt}
            {f"and date >= '{date_from.strftime('''%Y-%m-%d''')}'" if date_from else ''}
            {f"and date_start <= '{date_to.strftime('''%Y-%m-%d''')}'" if date_to else ''};
        """
        self.env.cr.execute(query)
        self.search([('user_id', '=', self.env.user.id)])._get_missing_data()

