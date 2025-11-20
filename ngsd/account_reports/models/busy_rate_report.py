import pytz
from odoo.tools.sql import column_exists, create_column
from odoo import models, fields, api, _
from odoo.tools.misc import format_date, DEFAULT_SERVER_DATE_FORMAT
from datetime import timedelta, datetime, time
from odoo.tools import config, date_utils, get_lang, html2plaintext
from dateutil.relativedelta import relativedelta
from decimal import localcontext, Decimal, ROUND_HALF_UP
from pytz import timezone, UTC
import math
from collections import defaultdict


class BusyRateReport(models.Model):
    _name = "busy.rate.report"
    _description = "Báo cáo Busy rate chi tiết"

    user_id = fields.Many2one('res.users')
    department_id = fields.Many2one('hr.department', string='Bộ phận/Đơn vị')
    employee_id = fields.Many2one('hr.employee', string='Họ tên nhân viên')
    work_email = fields.Char(string='Email')
    en_area_id = fields.Many2one(string='Khu vực', comodel_name='en.name.area')
    standard_hours = fields.Float(string='Tổng giờ làm việc chuẩn', compute='_get_missing_data', store=True)
    leave_hours = fields.Float(string='Tổng giờ nghỉ chế độ', compute='_get_missing_data', store=True)
    project_hours = fields.Float(string='Tổng giờ làm việc thực tế cho dự án')
    other_nonproject_hours = fields.Float(string='Tổng giờ các công việc khác dự án (công việc chung của trung tâm/Daily task, nghiên cứu, …) theo thực tế')
    kd_nonproject_hours = fields.Float(string='Tổng giờ công việc kinh doanh theo thực tế')
    presale_nonproject_hours = fields.Float(string='Tổng giờ presale theo thực tế')
    presale_nonproject_hours = fields.Float(string='Tổng giờ presale theo thực tế')
    support_project_hours = fields.Float(string='Tổng giờ hỗ trợ dự án theo thực tế')
    project_rate = fields.Float(string='Busy Rate dự án (%)', compute='_get_missing_data', store=True)
    other_rate = fields.Float(string='Busy Rate khác (%)', compute='_get_missing_data', store=True)
    kd_rate = fields.Float(string='Busy Rate Công việc kinh doanh (%)', compute='_get_missing_data', store=True)
    presale_rate = fields.Float(string='Busy Rate Presale (%)', compute='_get_missing_data', store=True)
    support_project_rate = fields.Float(string='Busy Rate Hỗ trợ dự án (%)', compute='_get_missing_data', store=True)
    all_rate = fields.Float(string='Busy Rate chung (%)', compute='_get_missing_data', store=True)
    type_employee_id = fields.Many2one('en.type', string='Loại nhân sự', related='employee_id.en_type_id')

    def _auto_init(self):
        self.env.cr.execute("""ALTER TABLE busy_rate_report 
            ADD COLUMN IF NOT EXISTS presale_nonproject_hours NUMERIC, 
            ADD COLUMN IF NOT EXISTS support_project_hours NUMERIC, 
            ADD COLUMN IF NOT EXISTS support_project_rate NUMERIC, 
            ADD COLUMN IF NOT EXISTS presale_rate NUMERIC""")
        return super()._auto_init()

    @api.depends('employee_id')
    def _get_missing_data(self):
        employees = self.employee_id
        employee_datas = dict.fromkeys(employees.ids)
        date_from, date_to = self._get_date_range()
        for employee in employees:
            tech_data = self.env['en.technical.model'].convert_daterange_to_data(employee, date_from, date_to)
            standard_hours = 0
            leave_hours = 0
            for d in tech_data:
                tech = tech_data.get(d)
                if tech and tech.get('tech') not in ['off'] and tech.get('tech_type') in ['leave', 'work']:
                    standard_hours += tech.get('number', 0)
                if tech and tech.get('tech') == 'leave' and tech.get('tech_type') in ['leave', 'holiday', 'leave_other']:
                    leave_hours += 8 - tech.get('number', 0)
            employee_datas[employee.id] = [leave_hours, standard_hours]
        for rec in self:
            try:
                leave_hours = employee_datas.get(rec.employee_id.id)[0]
                standard_hours = employee_datas.get(rec.employee_id.id)[1]
            except:
                print(rec.employee_id)
                print(employee_datas)
            rec.leave_hours = leave_hours
            rec.standard_hours = standard_hours
            rec.project_rate = rec.project_hours / standard_hours * 100 if standard_hours else 0
            rec.other_rate = rec.other_nonproject_hours / standard_hours * 100 if standard_hours else 0
            rec.kd_rate = rec.kd_nonproject_hours / standard_hours * 100 if standard_hours else 0
            rec.support_project_rate = rec.support_project_hours / standard_hours * 100 if standard_hours else 0
            rec.presale_rate = rec.presale_nonproject_hours / standard_hours * 100 if standard_hours else 0
            rec.all_rate = rec.project_rate + rec.other_rate + rec.kd_rate + rec.presale_rate + rec.support_project_rate

    @api.model
    def get_total_data(self, domain):
        datas = self.read_group(domain=domain, fields=['project_hours', 'standard_hours', 'leave_hours', 'other_nonproject_hours', 'kd_nonproject_hours', 'presale_nonproject_hours', 'support_project_hours'], groupby=['user_id'])
        data = datas and datas[0] or {}
        project_hours = data.get('project_hours') or 0
        standard_hours = data.get('standard_hours') or 0
        leave_hours = data.get('leave_hours') or 0
        kd_nonproject_hours = data.get('kd_nonproject_hours') or 0
        presale_nonproject_hours = data.get('presale_nonproject_hours') or 0
        support_project_hours = data.get('support_project_hours') or 0
        other_nonproject_hours = data.get('other_nonproject_hours') or 0
        if not standard_hours:
            return {'project_rate': 0, 'other_rate': 0, 'kd_rate': 0, 'all_rate': 0, 'presale_rate': 0}
        return {
            'project_rate': project_hours / standard_hours * 100,
            'other_rate': other_nonproject_hours / standard_hours * 100,
            'kd_rate': kd_nonproject_hours / standard_hours * 100,
            'presale_rate': presale_nonproject_hours / standard_hours * 100,
            'support_project_rate': support_project_hours / standard_hours * 100,
            'all_rate': (project_hours + other_nonproject_hours + kd_nonproject_hours + presale_nonproject_hours + support_project_hours) / standard_hours * 100,
        }

    def _get_date_range(self):
        date_from_txt = self._context.get('date_from') or fields.Date.Date.Date.context_today(self)
        date_to_txt = self._context.get('date_to') or fields.Date.Date.Date.context_today(self)
        date_from = min(fields.Date.from_string(date_from_txt), fields.Date.from_string(date_to_txt))
        date_to = max(fields.Date.from_string(date_from_txt), fields.Date.from_string(date_to_txt))

        min_date_from = date_from
        max_date_to = date_to
        final_date_from = max(min_date_from, date_from)
        final_date_to = min(max_date_to, date_to)

        datetime_from = datetime.combine(final_date_from, time.min)
        datetime_to = datetime.combine(final_date_to, time.max)
        return datetime_from, datetime_to

    def init_data(self):
        self = self.sudo()
        date_from, date_to = self._get_date_range()
        ctx = self._context
        type_employee_ids = ctx.get('type_employee_ids')
        # employee_ids = []
        user_tz = timezone(self.env.user.tz if self.env.user.tz else 'UTC')
        date_from_utc = user_tz.localize(date_from).astimezone(timezone('UTC'))
        date_to_utc = user_tz.localize(date_to).astimezone(timezone('UTC'))
        role_ids = self.env['entrust.role'].search([
            '|', ('name', 'ilike', 'GĐ Khối TV'), '|', ('name', 'ilike', 'GĐ SX'), '|', ('name', 'ilike', 'GĐ KD Khối'), '|', ('name', 'ilike', 'GĐ Khối'), ('name', 'ilike', 'GĐ Khu vực')
        ]).ids

        domain = [('user_id.role_ids', 'not in', role_ids), ('check_timesheet_before_checkout', '=', True)]
        type_ids = self.env['en.type'].search(['|', ('en_internal', '=', True), ('is_os', '=', True)]).ids
        if type_employee_ids:
            domain += [('en_type_id', 'in', type_employee_ids)]
        else:
            domain += [('en_type_id', 'in', type_ids)]
        # Nhân viên active
        employees = self.env['hr.employee'].search(domain + [
            ('en_date_start', '<=', date_to.date()), ('en_status', '=', 'active')
        ])
        # Nhân viên nghỉ việc trong tháng
        employees |= self.env['hr.employee'].with_context(active_test=False).search(domain + [
            ('en_date_start', '<=', date_to.date()), ('en_status', '=', 'inactive'), ('departure_date', '>', date_from.date())
        ])
        # trừ nhân viên nghỉ dài hạn trong tháng
        employees -= self.env['hr.employee'].with_context(active_test=False).search(domain + [
           ('en_day_layoff_from', '<', date_from.date()), ('en_day_layoff_to', '>', date_to.date())
        ])
        employee_ids = employees.ids
        employee_domain_txt = 'and employee_id in %s' % str(employee_ids).replace('[', '(').replace(']', ')') if employee_ids else ''
        employee_txt = 'and e.id in %s' % str(employee_ids).replace('[', '(').replace(']', ')') if employee_ids else ''

        query = f"""
            DELETE FROM {self._table} WHERE user_id = {self.env.user.id};
            with
            ts as (
                select employee_id, sum(unit_amount) unit_amount
                from account_analytic_line
                where en_state = 'approved'
                    and project_id is not null
                    and employee_id is not null
                    and extract(dow from date) not in (0, 6)
                    {employee_domain_txt}
                    {f"and date >= '{date_from.strftime('''%Y-%m-%d''')}'" if date_from else ''}
                    {f"and date <= '{date_to.strftime('''%Y-%m-%d''')}'" if date_to else ''}
                group by employee_id
            ),
            ot as (
                select employee_id, sum(time) AS total_hours
                from en_hr_overtime
                where state = 'approved'
                    and project_id is not null
                    and employee_id is not null
                    {employee_domain_txt}
                    {f"and date_to >= '{date_from_utc.strftime('''%Y-%m-%d %H:%M:%S''')}'" if date_from else ''}
                    {f"and date_from <= '{date_to_utc.strftime('''%Y-%m-%d %H:%M:%S''')}'" if date_to else ''}
                group by employee_id
            ),
            
            ts_nonproject as (
                select a.employee_id,
                    sum(CASE WHEN task.en_task_type in ('daily', 'waiting_task') THEN a.unit_amount ELSE 0 END) daily_hours,
                    sum(CASE WHEN task.en_task_type = 'presale' THEN a.unit_amount ELSE 0 END) presale_hours,
                    sum(CASE WHEN task.en_task_type = 'support' THEN a.unit_amount ELSE 0 END) support_hours,
                    sum(CASE WHEN task.en_task_type = 'support_project' THEN a.unit_amount ELSE 0 END) support_project_hours
                from account_analytic_line a
                join en_nonproject_task task on a.en_nonproject_task_id = task.id
                where a.en_state = 'approved'
                    and a.project_id is null
                    and a.employee_id is not null
                    and extract(dow from date) not in (0, 6)
                    {employee_domain_txt}
                    {f"and date >= '{date_from.strftime('''%Y-%m-%d''')}'" if date_from else ''}
                    {f"and date <= '{date_to.strftime('''%Y-%m-%d''')}'" if date_to else ''}
                group by a.employee_id
            ),
            ot_nonproject as (
                select o.employee_id,
                    sum(CASE WHEN task.en_task_type in ('daily', 'waiting_task') THEN o.time ELSE 0 END) daily_hours,
                    sum(CASE WHEN task.en_task_type = 'presale' THEN o.time ELSE 0 END) presale_hours,
                    sum(CASE WHEN task.en_task_type = 'support' THEN o.time ELSE 0 END) support_hours,
                    sum(CASE WHEN task.en_task_type = 'support_project' THEN o.time ELSE 0 END) support_project_hours
                from en_hr_overtime o
                join en_nonproject_task task on o.en_nonproject_task_id = task.id
                where o.state = 'approved'
                    and o.employee_id is not null
                    {employee_domain_txt}
                    {f"and o.date_to >= '{date_from.strftime('''%Y-%m-%d''')}'" if date_from else ''}
                    {f"and o.date_from <= '{date_to.strftime('''%Y-%m-%d''')}'" if date_to else ''}
                group by o.employee_id
            )
            INSERT INTO {self._table} (employee_id, work_email, department_id, en_area_id, project_hours, other_nonproject_hours, kd_nonproject_hours, presale_nonproject_hours, support_project_hours, user_id)
            select
                e.id,
                e.work_email,
                e.department_id,
                e.en_area_id,
                coalesce(unit_amount, 0) + coalesce(total_hours, 0) total_hours,
                coalesce(ot_nonproject.daily_hours, 0) + coalesce(ts_nonproject.daily_hours, 0) daily_hours,
                coalesce(ot_nonproject.support_hours, 0) + coalesce(ts_nonproject.support_hours, 0) support_hours,
                coalesce(ot_nonproject.presale_hours, 0) + coalesce(ts_nonproject.presale_hours, 0) presale_hours,
                coalesce(ot_nonproject.support_project_hours, 0) + coalesce(ts_nonproject.support_project_hours, 0) support_project_hours,
                {self.env.user.id}
            from hr_employee e
            left join ts on e.id = ts.employee_id
            left join ot on e.id = ot.employee_id
            left join ts_nonproject on e.id = ts_nonproject.employee_id
            left join ot_nonproject on e.id = ot_nonproject.employee_id
            where 1=1
            {employee_txt};
        
        """
        self.env.cr.execute(query)
        self.search([('user_id', '=', self.env.user.id)])._get_missing_data()

