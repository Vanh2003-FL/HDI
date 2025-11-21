from odoo import models, fields, api, _
from odoo.tools import date_utils
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from decimal import Decimal, ROUND_HALF_UP


class ProjectResourceSummary(models.Model):
    _name = 'project.resource.summary'
    _description = 'Tổng hợp nguồn lực dự án'

    project_id = fields.Many2one('project.project', string='Dự án', required=True, index=True)
    project_code = fields.Char(string='Mã dự án', related='project_id.en_code', store=True, readonly=True)
    criteria_type = fields.Selection([
        ('plan', 'Plan'),
        ('actual', 'Actual')
    ], string='Loại tiêu chí', required=True, index=True)
    month = fields.Char(string='Tháng', required=True, help='Định dạng MM/YYYY', index=True)
    value = fields.Float(string='Giá trị', digits=(16, 3), default=0.0, required=True)

    # TODO: Migrate _sql_constraints to individual models.Constraint objects
    _sql_constraints = [
        ('unique_project_criteria_month', 'UNIQUE(project_id, criteria_type, month)',
         'Kết hợp Dự án, Loại tiêu chí và Tháng phải là duy nhất.')
    ]

    @api.model
    def _compute_resource_summary(self):
        """Cron job để tính toán và cập nhật dữ liệu tổng hợp nguồn lực."""
        # Xóa dữ liệu cũ để tránh trùng lặp
        self.search([]).unlink()

        # Lấy tất cả dự án
        projects = self.env['project.project'].search([])
        today = fields.Date.today()
        # Duyệt qua từng dự án
        for project in projects:
            if not project.date_start or not project.mm_rate:
                continue

            date_start = project.date_start
            date_end = today + relativedelta(months=1, day=1, days=-1)
            datetime_from = datetime.combine(date_start, datetime.min.time())
            datetime_to = datetime.combine(date_end, datetime.max.time())

            # Tính toán cho từng tháng trong khoảng thời gian
            for date_step in date_utils.date_range(datetime_from, datetime_to, relativedelta(months=1)):
                month_txt = date_step.strftime('%m/%Y')
                compared_from = max(date_step + relativedelta(day=1), datetime_from).date()
                compared_to = min(date_step + relativedelta(months=1, day=1, days=-1), datetime_to).date()

                # Tính Plan
                plan_value = 0.0
                for line in project.en_resource_id.order_line:
                    start_plan = line.date_start
                    end_plan = min(line.date_end, compared_to)
                    employee = line.employee_id
                    hours = self.env['en.technical.model'].convert_daterange_to_hours(
                        employee, max(start_plan, compared_from), min(compared_to, end_plan))
                    plan_value += hours * line.workload
                plan_value = plan_value / 8 / project.mm_rate if project.mm_rate else 0
                plan_value += sum(project.en_history_resource_ids.filtered(
                    lambda x: (int(x.month) == compared_from.month and int(x.year) == compared_from.year)
                ).mapped('plan'))
                plan_value = float(Decimal(str(plan_value)) * 1000) / 1000

                # Tính Actual
                actual_value = 0.0
                for line in self.env['account.analytic.line'].sudo().search([
                    ('project_id', '=', project.id),
                    ('date', '>=', compared_from),
                    ('date', '<=', compared_to)
                ]):
                    if line.en_state == 'approved':
                        actual_value += line.unit_amount
                    if line.ot_state == 'approved':
                        actual_value += line.ot_time
                actual_value = actual_value / 8 / project.mm_rate if project.mm_rate else 0
                actual_value += sum(project.en_history_resource_ids.filtered(
                    lambda x: (int(x.month) == compared_from.month and int(x.year) == compared_from.year)
                ).mapped('actual'))
                actual_value = float(Decimal(str(actual_value)) * 1000) / 1000

                # Tạo bản ghi Plan
                if plan_value:
                    self.create({
                        'project_id': project.id,
                        'criteria_type': 'plan',
                        'month': month_txt,
                        'value': plan_value
                    })

                # Tạo bản ghi Actual
                if actual_value:
                    self.create({
                        'project_id': project.id,
                        'criteria_type': 'actual',
                        'month': month_txt,
                        'value': actual_value
                    })

    @api.model
    def _schedule_compute_resource_summary(self):
        """Cấu hình cron job chạy lúc 00:00 hàng ngày."""
        print('------- LOAD RESOURCE SUMMARY -------')
        self._compute_resource_summary()

