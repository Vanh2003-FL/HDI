import math
import logging
from datetime import datetime, time, timedelta
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models
_logger = logging.getLogger(__name__)


class TechnicalModel(models.Model):
    _inherit = "en.technical.model"

    def _auto_init(self):
        self._cr.execute("""alter table en_technical_model
            add column if not exists expense numeric;""")
        return super()._auto_init()

    expense = fields.Integer(string="Chi phí", compute='_compute_expense', compute_sudo=True, store=True)

    def get_month_expense(self):
        """
        Tính chi phí tháng cho từng bản ghi: nhân viên X vào ngày Y thuộc tháng Z.
        Trả về {record_id: chi phí tháng}.
        """
        result = {}
        for rec in self:
            employee = rec.employee_id
            rec_date = rec.date
            expense = 0
            if employee.is_os:
                # Chi phí nhân sự thuê ngoài
                os_expense = employee.os_expense_ids.filtered(lambda x: x.date_start <= rec_date and (not x.date_end or rec_date <= x.date_end))
                if os_expense:
                    expense = os_expense.expense
            else:
                # Chi phí nội bộ
                history_level = employee.history_level_ids.filtered(
                    lambda x: x.date_start <= rec_date and (not x.date_end or rec_date <= x.date_end))
                if history_level:
                    level = history_level.level_id
                    expense_lines = level.expense_ids.filtered(
                        lambda x: x.date_start <= rec_date <= x.date_end and employee.department_id.id in x.department_ids.ids)
                    for line in expense_lines:
                        expense = line.expense
                        break
            result[rec.id] = expense
        return result

    def get_day_expenses(self):
        """
        Trả về chi phí tính theo ngày (dựa trên chi phí tháng chia số ngày làm việc).
        """
        month_expenses = self.get_month_expense()
        workday_cache = {}  # {employee_id: {month_start: num_working_days}}
        result = {}
        for rec in self:
            employee = rec.employee_id
            rec_date = rec.date
            expense = 0
            month_expense = month_expenses.get(rec.id, 0)
            if month_expense:
                month_start = datetime.combine(rec_date.replace(day=1), time.min)
                month_end = datetime.combine((rec_date + relativedelta(months=1, day=1)) - timedelta(days=1), time.max)
                if employee.is_os:
                    expense = month_expense  # Trả chi phí nguyên tháng
                else:
                    if employee.id not in workday_cache:
                        workday_cache[employee.id] = {}
                    if month_start not in workday_cache[employee.id]:
                        working_days = self.env['en.technical.model'].convert_daterange_to_count(
                            employee, month_start, month_end, exclude_tech_type=['off', 'holiday'])
                        workday_cache[employee.id][month_start] = working_days
                    num_days = workday_cache[employee.id][month_start]
                    expense = month_expense / num_days if num_days > 0 else 0
            result[rec.id] = math.ceil(expense)
        return result

    def convert_daterange_to_expense(self, employee, start_date, end_date, exclude_tech=None, exclude_tech_type=None):
        """
        Tính tổng chi phí theo khoảng thời gian (dựa trên dữ liệu từng ngày).
        """
        if start_date > end_date:
            return 0
        domain = [
            ('employee_id', '=', employee.id),
            ('date', '>=', start_date),
            ('date', '<=', end_date),
        ]
        if exclude_tech:
            domain.append(('tech', 'not in', exclude_tech))
        if exclude_tech_type:
            domain.append(('tech_type', 'not in', exclude_tech_type))
        records = self.search(domain)
        expenses = records.get_day_expenses()
        return sum(expenses.values())

    @api.depends('tech_type', 'employee_id', 'employee_id.history_level_ids', 'employee_id.os_expense_ids',
                 'employee_id.os_expense_ids')
    def _compute_expense(self):
        records = self.filtered(lambda x: x.date and x.employee_id)
        expenses = records.get_day_expenses()
        for rec in self:
            rec.expense = expenses.get(rec.id, 0)

    @api.model
    def _recompute_expense_batch(self, record_ids):
        if not record_ids:
            return
        cr = self.env.cr
        batch_recordset = self.browse(record_ids)
        expenses = batch_recordset.get_day_expenses()
        if not expenses:
            return
        values_sql = ", ".join(
            cr.mogrify("(%s, %s)", (rec_id, expense)).decode("utf-8")
            for rec_id, expense in expenses.items()
        )
        query = f"""
                UPDATE en_technical_model
                SET expense = data.expense
                FROM (VALUES {values_sql}) AS data(id, expense)
                WHERE en_technical_model.id = data.id
            """
        cr.execute(query)

    def _recompute_expense(self):
        if not self:
            return
        batch_size = 20000
        all_ids = self.ids
        for start in range(0, len(all_ids), batch_size):
            end = start + batch_size
            batch_ids = all_ids[start:end]
            self.with_delay()._recompute_expense_batch(batch_ids)
