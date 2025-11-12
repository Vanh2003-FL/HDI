from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
from decimal import localcontext, ROUND_HALF_UP
from collections import defaultdict


class TimesheetDetailByProject(models.Model):
    _name = "timesheet.detail.by.project"
    _description = "Báo cáo chi tiết Timesheet theo dự án"

    user_id = fields.Many2one('res.users')
    barcode = fields.Char(string='Mã nhân viên')
    work_email = fields.Char(string='Email')
    employee_id = fields.Many2one('hr.employee', string='Tên nhân viên')
    department_id = fields.Many2one('hr.department', string='Phòng ban/Trung tâm')
    en_status = fields.Char(string='Trạng thái hoạt động')
    project_code = fields.Char(string='Mã dự án')
    project_name = fields.Char(string='Dự án/Phòng/Ban/Trung tâm')
    timesheet_hours = fields.Float(string='Số giờ làm việc trong dự án/ phòng /Ban/trung tâm')
    project_stage = fields.Char(string='Giai đoạn dự án')
    ot_hours = fields.Float(string='Số giờ làm thêm trong dự án/ phòng /Ban/trung tâm')
    work_days = fields.Float(string='Số ngày làm việc')
    total_timesheet_hours = fields.Float(string='Tổng giờ làm việc thực tế')
    total_ot_hours = fields.Float(string='Tổng giờ làm thêm thực tế')

    def init_data(self):
        vals = self._get_lines()
        query = f'DELETE FROM {self._table} WHERE user_id = {self.env.user.id};'
        self.env.cr.execute(query)
        self.create(vals)

    def _get_lines(self):
        lines = []
        self = self.sudo()
        ctx = self._context
        employee_ids = ctx.get('employee_ids')
        date_from_txt = self._context.get('date_from') or fields.Date.Date.context_today(self)
        date_to_txt = self._context.get('date_to') or fields.Date.Date.context_today(self)

        date_from = fields.Date.from_string(date_from_txt)
        date_to = fields.Date.from_string(date_to_txt)

        employee_domain = ['|', '|', ('departure_date', '>=', date_to), ('departure_date', '=', False), '&',
                           ('departure_date', '>=', date_from), ('departure_date', '<=', date_to)]
        if employee_ids:
            employee_domain += [('id', 'in', tuple(employee_ids))]

        employes = self.env['hr.employee'].with_context(active_test=False).search(employee_domain)

        # Thay đổi logic: không ép về đầu/tháng - cuối/tháng
        # Sẽ lấy đúng khoảng thời gian người dùng chọn trong wizard
        final_date_from = date_from
        final_date_to = date_to

        en_status_map = dict(employes.fields_get(['en_status'])['en_status']['selection'])
        user_id = self.env.user.id

        with localcontext() as ctx:
            ctx.rounding = ROUND_HALF_UP

            datas_per_project_employee, phase_ids = self.query_project(employee_ids, final_date_from,
                                                                       final_date_to) or {}
            datas_nonproject_per_employee = self.query_nonproject(employee_ids, final_date_from, final_date_to) or {}

            phase = self.env['project.task'].search([('id', 'in', tuple(phase_ids))])

            # Tạo dict với id là key
            id_to_phase = {item['id']: item['name'] for item in phase}

            for employee in employes:
                # TS các dự án
                data_project_per_employee = datas_per_project_employee.get(employee.id)
                # TS ngoài dự án
                data_nonproject_per_employee = datas_nonproject_per_employee.get(employee.id)
                if not data_project_per_employee and not data_nonproject_per_employee:
                    continue

                data_project_per_employee = data_project_per_employee or {}
                data_nonproject_per_employee = data_nonproject_per_employee or [0, 0, 0]

                # Tính tổng timesheet và overtime từ tất cả project_id và task_id
                total_ts_project = 0
                total_ot_project = 0
                for project_id, stages in data_project_per_employee.items():
                    for task_id, values in stages.items():
                        total_ts_project += values[0]  # unit_amount
                        total_ot_project += values[1]  # time

                # Cộng thêm từ non-project
                total_ts_project += data_nonproject_per_employee[0]
                total_ot_project += data_nonproject_per_employee[1]

                # line TS các dự án
                for project_id, stages in data_project_per_employee.items():
                    for task_id, data_per_project in stages.items():
                        project = self.env['project.project'].browse(project_id)
                        columns = {
                            'user_id': user_id,
                            'barcode': employee.barcode,
                            'work_email': employee.work_email or '',
                            'employee_id': employee.id,
                            'department_id': employee.department_id.id,
                            'en_status': en_status_map.get(employee.en_status) or '',
                            'project_code': project.en_code or '',
                            'project_name': project.name or '',
                            'project_stage': id_to_phase.get(task_id) or '',
                            'timesheet_hours': data_per_project[0] or 0,  # unit_amount
                            'ot_hours': data_per_project[1] or 0,  # time
                            'work_days': data_per_project[2] or 0,  # count_ts
                            'total_timesheet_hours': total_ts_project or 0,
                            'total_ot_hours': total_ot_project or 0,
                        }
                        lines.append(columns)

                if data_nonproject_per_employee != [0, 0, 0]:
                    # line TS ngoài dự án
                    columns = {
                        'user_id': user_id,
                        'barcode': employee.barcode,
                        'work_email': employee.work_email or '',
                        'employee_id': employee.id,
                        'department_id': employee.department_id.id,
                        'en_status': en_status_map.get(employee.en_status) or '',
                        'project_code': '',
                        'project_name': employee.department_id.display_name or '',
                        'timesheet_hours': data_nonproject_per_employee[0] or 0,
                        'ot_hours': data_nonproject_per_employee[1] or 0,
                        'work_days': data_nonproject_per_employee[2] or 0,
                        'total_timesheet_hours': total_ts_project or 0,
                        'total_ot_hours': total_ot_project or 0,
                    }
                    lines.append(columns)

        return lines

    def query_project(self, employee_ids, start_date, end_date):
        start_date = start_date and start_date
        end_date = end_date and end_date
        employee_domain = (
            'and employee_id in %s' % str(employee_ids).replace('[', '(').replace(']', ')')
            if employee_ids else ''
        )

        query = f"""
            WITH RECURSIVE task_hierarchy AS (
                SELECT
                    id AS task_id,
                    id AS current_id,
                    parent_id,
                    category
                FROM project_task
                WHERE category = 'task'
                UNION ALL
                SELECT
                    th.task_id,
                    t.id AS current_id,
                    t.parent_id,
                    t.category
                FROM project_task t
                JOIN task_hierarchy th ON t.id = th.parent_id
            ),
            task_to_phase AS (
                SELECT
                    task_id,
                    current_id AS phase_id
                FROM task_hierarchy
                WHERE category = 'phase'
            )
            SELECT
                aal.employee_id,
                aal.project_id,
                COALESCE(tp.phase_id, aal.task_id) AS phase_id,
                SUM(CASE WHEN aal.en_state = 'approved' THEN aal.unit_amount ELSE 0 END) AS unit_amount,
                SUM(CASE WHEN aal.ot_state = 'approved' THEN aal.ot_time ELSE 0 END) AS ot_time,
                COUNT(DISTINCT aal.date) AS count_ts
            FROM account_analytic_line aal
            LEFT JOIN task_to_phase tp ON aal.task_id = tp.task_id
            WHERE (aal.en_state = 'approved' or aal.ot_state = 'approved')
                AND aal.project_id IS NOT NULL
                AND aal.employee_id IS NOT NULL
                {employee_domain}
                {f"and aal.date >= '{start_date.strftime('%Y-%m-%d')}'" if start_date else ''}
                {f"and aal.date <= '{end_date.strftime('%Y-%m-%d')}'" if end_date else ''}
            GROUP BY
                aal.employee_id,
                aal.project_id,
                COALESCE(tp.phase_id, aal.task_id);
        """

        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()

        data_per_project_employee = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        phase_ids = []

        for res in result:
            data_per_project_employee[res['employee_id']][res['project_id']][res['phase_id']] = [
                res['unit_amount'],
                res['ot_time'],
                res['count_ts']
            ]
            if res['phase_id'] not in phase_ids:
                phase_ids.append(res['phase_id'])

        return data_per_project_employee, phase_ids

    def query_nonproject(self, employee_ids, start_date, end_date):
        start_date = start_date and start_date
        end_date = end_date and end_date
        employee_domain = 'and employee_id in %s' % str(employee_ids).replace('[', '(').replace(']',
                                                                                                ')') if employee_ids else ''
        query = f"""
            with
            ts as (
                select employee_id, sum(unit_amount) unit_amount, count(DISTINCT date) count_ts
                from account_analytic_line
                where en_state = 'approved'
                    and project_id is null
                    and employee_id is not null
                    {employee_domain}
                    {f"and date >= '{start_date.strftime('''%Y-%m-%d''')}'" if start_date else ''}
                    {f"and date <= '{end_date.strftime('''%Y-%m-%d''')}'" if end_date else ''}
                group by employee_id
            ),
            ot as (
                select employee_id, sum(time) AS time
                from en_hr_overtime
                where state = 'approved'
                    and project_id is null
                    and employee_id is not null
                    {employee_domain}
                    {f"and date >= '{start_date.strftime('''%Y-%m-%d''')}'" if start_date else ''}
                    {f"and date <= '{end_date.strftime('''%Y-%m-%d''')}'" if end_date else ''}
                group by employee_id
            )

            select coalesce(ot.employee_id, ts.employee_id) employee_id,
                coalesce(unit_amount, 0) unit_amount,
                coalesce(time, 0) AS time,
                coalesce(count_ts, 0) count_ts
            from ts
            full join ot on ot.employee_id = ts.employee_id
        """
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()
        data_per_employee = defaultdict(list)
        for res in result:
            data_per_employee[res['employee_id']] = [res['unit_amount'], res['time'], res['count_ts']]
        return data_per_employee
