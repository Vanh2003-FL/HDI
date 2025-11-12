import base64
import io

import xlsxwriter
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api
from datetime import timedelta, datetime, date
import logging

from odoo.fields import Date

_logger = logging.getLogger(__name__)


class ProjectQualityMonthlyReport(models.Model):
    _name = 'project.quality.monthly.report'
    _description = 'Báo cáo chỉ tiêu chất lượng dự án hàng tháng'
    _order = 'center_name'
    _rec_name = False

    unit_name = fields.Char(string='Khối')
    center_name = fields.Char(string='Trung tâm')
    project_type = fields.Char(string='Loại dự án')
    project_code = fields.Char(string='Dự án')
    project_management = fields.Char(string='Quản lý dự án')
    project_manager = fields.Char(string='Giám đốc dự án')
    qa_name = fields.Char(string="QA")
    project_status = fields.Char(string='Trạng thái dự án')
    report_month = fields.Date(string='Date')
    planned_start_date = fields.Date(string='Planned Start Date')
    planned_release_date = fields.Date(string='Planned Release Date KH vlast')
    package_code = fields.Char(string='Mã gói việc cuối của tháng tính chỉ tiêu')
    actual_start_date = fields.Date(string='Actual Start Date')
    actual_end_date = fields.Date(string='Actual End Date')
    target_calculation_date = fields.Date(string='Ngày tính chỉ tiêu')
    planned_effort_month = fields.Float(string='Nguồn lực kế hoạch tháng theo KHNL Lastupdate')
    actual_effort_month = fields.Float(string='Nguồn lực thực tế trong tháng')
    planned_effort_cumulative = fields.Float(string='Nguồn lực kế hoạch tích lũy theo v.lastUpdate')
    actual_effort_cumulative = fields.Float(string='Tổng nguồn lực thực tế tích lũy')
    schedule_achievement_last = fields.Float(string='% Schedule Achievement v Lastupdate')
    effort_efficiency_monthly = fields.Float(string='% Effort Efficiency Monthly')
    effort_efficiency_plan_last = fields.Float(string='% Efficiency plan v Lastupdate')

    @api.model
    def export_excel_report(self, filters):
        domain = []

        # Xử lý filter tháng
        if filters.get('months'):
            months = sorted(filters['months'])
            if len(months) == 1:
                month_str = months[0]
                domain.append(('report_month', 'like', f'{month_str}%'))
            else:
                start_month = months[0]
                end_month = months[-1]
                domain.append(('report_month', '>=', fields.Date.to_date(f'{start_month}-01')))
                domain.append(
                    ('report_month', '<=', fields.Date.end_of(fields.Date.to_date(f'{end_month}-01'), 'month')))

        # Các filter khác
        if filters.get('khoi'):
            domain.append(('unit_name', '=', filters['khoi']))
        if filters.get('trung_tam'):
            domain.append(('center_name', '=', filters['trung_tam']))
        if filters.get('loai_du_an'):
            domain.append(('project_type', '=', filters['loai_du_an']))
        if filters.get('du_an'):
            if isinstance(filters['du_an'], list):
                domain.append(('project_code', 'in', filters['du_an']))
            else:
                domain.append(('project_code', '=', filters['du_an']))
        else:
            prj_code = self.env['project.project'].search([]).mapped('en_code')
            domain.append(('project_code', 'in', prj_code))

        reports = self.search(domain)

        # Tạo file Excel
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet("Quality Report")

        # Định dạng
        header_format = workbook.add_format({
            'bold': True,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#D9D9D9',
            'text_wrap': True
        })

        sub_header_format = workbook.add_format({
            'bold': True,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#EAEAEA',
            'text_wrap': True
        })

        cell_format = workbook.add_format({
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True
        })

        # Lấy danh sách tháng từ filter
        selected_months = sorted(filters.get('months', []))

        # Tạo header - Dòng 0: Các tháng (merge cells)
        worksheet.merge_range(0, 0, 1, 0, 'STT', header_format)
        worksheet.merge_range(0, 1, 1, 1, 'Khối', header_format)
        worksheet.merge_range(0, 2, 1, 2, 'Trung tâm', header_format)
        worksheet.merge_range(0, 3, 1, 3, 'Loại dự án', header_format)
        worksheet.merge_range(0, 4, 1, 4, 'Mã dự án', header_format)

        # Merge cells cho các tháng và tạo sub-header
        col_start = 5
        for month in selected_months:
            # Merge cell cho tên tháng (2 hàng)
            worksheet.merge_range(0, col_start, 0, col_start + 2, month, header_format)

            # Sub-header cho các chỉ số
            worksheet.write(1, col_start, '%Schedule', sub_header_format)
            worksheet.write(1, col_start + 1, '%Effort Monthly', sub_header_format)
            worksheet.write(1, col_start + 2, '%Effort Plan', sub_header_format)

            col_start += 3

        # Nhóm dữ liệu theo dự án
        projects_data = {}
        for report in reports:
            project_key = (report.unit_name, report.center_name, report.project_type, report.project_code)
            month_key = fields.Date.to_string(report.report_month)[:7] if report.report_month else ''

            if project_key not in projects_data:
                projects_data[project_key] = {}

            projects_data[project_key][month_key] = {
                'schedule': report.schedule_achievement_last or 0,
                'effort_monthly': report.effort_efficiency_monthly or 0,
                'effort_plan': report.effort_efficiency_plan_last or 0
            }

        # Ghi dữ liệu
        for row_idx, (project_key, months_data) in enumerate(projects_data.items(), start=2):
            unit_name, center_name, project_type, project_code = project_key

            # Ghi thông tin cố định
            worksheet.write(row_idx, 0, row_idx - 1, cell_format)  # STT
            worksheet.write(row_idx, 1, unit_name, cell_format)  # Khối
            worksheet.write(row_idx, 2, center_name, cell_format)  # Trung tâm
            worksheet.write(row_idx, 3, project_type, cell_format)  # Loại dự án
            worksheet.write(row_idx, 4, project_code, cell_format)  # Mã dự án

            # Ghi dữ liệu theo tháng
            col = 5
            for month in selected_months:
                if month in months_data:
                    data = months_data[month]
                    worksheet.write_number(row_idx, col, data['schedule'], cell_format)
                    worksheet.write_number(row_idx, col + 1, data['effort_monthly'], cell_format)
                    worksheet.write_number(row_idx, col + 2, data['effort_plan'], cell_format)
                else:
                    worksheet.write(row_idx, col, '-', cell_format)
                    worksheet.write(row_idx, col + 1, '-', cell_format)
                    worksheet.write(row_idx, col + 2, '-', cell_format)
                col += 3

        # Tự động điều chỉnh độ rộng cột
        column_widths = {
            0: 5,  # STT
            1: 30,  # Khối
            2: 30,  # Trung tâm
            3: 30,  # Loại dự án
            4: 30  # Mã dự án
        }

        # Đặt độ rộng cho các cột thông tin
        for col, width in column_widths.items():
            worksheet.set_column(col, col, width)

        # Đặt độ rộng cho các cột chỉ số (12 cho mỗi cột)
        for col in range(5, 5 + len(selected_months) * 3):
            worksheet.set_column(col, col, 15)

        # Đặt chiều cao hàng
        worksheet.set_row(0, 20)
        worksheet.set_row(1, 20)

        workbook.close()
        output.seek(0)

        return {
            'file_name': 'Bao Cao Chi Tieu Chat Luong dự án hàng tháng.xlsx',
            'file_data': base64.b64encode(output.read()).decode('utf-8')
        }

    @api.model
    def get_filtered_reports(self, filters):
        domain = []

        if filters.get('trung_tam'):
            domain.append(('center_name', '=', filters['trung_tam']))
        if filters.get('khoi'):
            domain.append(('unit_name', '=', filters['khoi']))
        if filters.get('loai_du_an'):
            domain.append(('project_type', '=', filters['loai_du_an']))
        if filters.get('du_an'):
            du_an_list = filters['du_an'] if isinstance(filters['du_an'], list) else [filters['du_an']]
            domain.append(('project_code', 'in', du_an_list))
        else:
            projects = self.env['project.project'].search([])
            project_codes = [project.en_code for project in projects]
            domain.append(('project_code', 'in', project_codes))

        # Xử lý filter nhiều tháng
        if filters.get('months'):
            month_list = filters['months'] if isinstance(filters['months'], list) else [filters['months']]
            month_domains = []
            for month_str in month_list:
                try:
                    start_date = datetime.strptime(month_str, '%Y-%m').date()
                    end_date = start_date + relativedelta(months=1)
                    month_domains.append(['&', ('report_month', '>=', start_date), ('report_month', '<', end_date)])
                except ValueError:
                    continue

            if filters.get('months'):
                # Chuyển list tháng dạng YYYY-MM thành list ngày đầu tháng
                month_list = filters['months'] if isinstance(filters['months'], list) else [filters['months']]
                date_objs = []
                for month_str in month_list:
                    try:
                        date_objs.append(datetime.strptime(month_str, '%Y-%m').date())
                    except ValueError:
                        continue

                if date_objs:
                    domain.append(('report_month', 'in', date_objs))

        # Truy vấn dữ liệu
        records = self.sudo().search_read(domain, [
            'unit_name', 'center_name', 'project_type', 'project_code',
            'report_month', 'schedule_achievement_last',
            'effort_efficiency_monthly', 'effort_efficiency_plan_last'
        ])

        # ==== Group dữ liệu theo project_code và tháng ====
        grouped_data = {}
        for rec in records:
            project_key = rec['project_code']
            month_key = rec['report_month'].strftime('%Y-%m')

            if project_key not in grouped_data:
                grouped_data[project_key] = {
                    'project_code': project_key,
                    'unit_name': rec['unit_name'],
                    'center_name': rec['center_name'],
                    'project_type': rec['project_type'],
                    'values': {}
                }

            grouped_data[project_key]['values'][month_key] = {
                'schedule_achievement_last': rec['schedule_achievement_last'],
                'effort_efficiency_monthly': rec['effort_efficiency_monthly'],
                'effort_efficiency_plan_last': rec['effort_efficiency_plan_last'],
            }

        # ==== Norm data ====
        norm_settings = self.env['reporting.norm.setting'].sudo().search_read([], [])
        norm_map = {
            norm['short_name']: {
                'value': norm['norm_value'],
                'std_dev': norm['standard_deviation'],
                'direction': norm['satisfactory_direction'],
                'color_good': norm['color_good'],
                'color_pass': norm['color_pass'],
                'color_fail': norm['color_fail'],
                'color_bad': norm['color_bad'],
            }
            for norm in norm_settings
        }
        return {
            'months': filters.get('months', []),
            'projects': list(grouped_data.values()),
            'norm': norm_map,

        }

    @api.model
    def get_filter_values(self, filters=None):
        allowed_project_codes = self.env['project.project'].search([]).mapped('en_code')

        domain = [('project_code', 'in', allowed_project_codes)]

        if not filters:
            filters = {}

        if filters.get('months'):
            month_list = filters['months'] if isinstance(filters['months'], list) else [filters['months']]
            try:
                dates = [datetime.strptime(m, '%Y-%m').date() for m in month_list]
                domain.append(('report_month', 'in', dates))
            except Exception:
                pass

        if filters.get('khoi'):
            domain.append(('unit_name', '=', filters['khoi']))
        if filters.get('center'):
            domain.append(('center_name', '=', filters['center']))
        if filters.get('type'):
            domain.append(('project_type', '=', filters['type']))
        if filters.get('project'):
            project_codes = filters['project'] if isinstance(filters['project'], list) else [filters['project']]
            domain.append(('project_code', 'in', project_codes))

        records = self.search(domain)

        def clean(values):
            return sorted(set(v for v in values if v))

        project_info = [{
            'project_code': rec.project_code,
            'unit_name': rec.unit_name,
            'center_name': rec.center_name,
            'project_type': rec.project_type,
        } for rec in records]

        return {
            'centers': clean(records.mapped('center_name')),
            'unit_name': clean(records.mapped('unit_name')),
            'project_types': clean(records.mapped('project_type')),
            'projects': clean(records.mapped('project_code')),
            'months': clean(records.mapped('report_month')),
            'project_details': project_info,
        }

    @api.model
    def generate_monthly_report(self, start_month=None, end_month=None, project_code=None):

        target_calculation_date = None

        def to_date(val):
            if isinstance(val, datetime):
                return val.date()
            elif isinstance(val, date):
                return val
            elif isinstance(val, str):
                return datetime.strptime(val, "%d/%m/%Y").date()
            return None

        def round_float(value, precision=2):
            try:
                return round(float(value), precision)
            except (TypeError, ValueError):
                return 0.0

        today = fields.Date.today()
        # Xử lý logic start_month và end_month
        if not start_month:
            if project_code:
                # Truyền project_code mà không truyền start_month → lấy tháng hiện tại
                start_month = today.replace(day=1)
            elif today.day == 1:
                # Không có project_code và hôm nay là mùng 1 → lấy tháng trước
                start_month = (today - relativedelta(months=1)).replace(day=1)
            else:
                # Không có project_code và không phải mùng 1 → không tính
                return
        else:
            # Nếu có truyền start_month
            start_month = fields.Date.from_string(start_month) if isinstance(start_month, str) else start_month
            if not end_month:
                # Chỉ truyền start_month → lùi 1 tháng
                start_month = (start_month - relativedelta(months=1)).replace(day=1)
            else:
                # Truyền cả start và end → giữ nguyên
                start_month = start_month.replace(day=1)

        # Xử lý end_month
        if not end_month:
            end_month = start_month
        else:
            end_month = fields.Date.from_string(end_month) if isinstance(end_month, str) else end_month
            end_month = end_month.replace(day=1)

        months = []
        current_month = start_month
        while current_month <= end_month:
            months.append(current_month)
            current_month += relativedelta(months=1)

        if project_code:
            projects = self.env['project.project'].search([('en_code', '=', project_code)])
        else:
            projects = self.env['project.project'].search([('stage_id', '=', 3)])


        for month_start in months:
            month_end = (month_start + relativedelta(months=1)) - timedelta(days=1)
            target_calculation_date = (month_start + relativedelta(months=1)) - timedelta(days=1)

            for project in projects:
                actual_start = None
                #  Ngày bắt đầu thực tế theo timesheet
                self.env.cr.execute("""
                               SELECT ac.id, ac.technical_field_27607_1
                               FROM account_analytic_line AS ac
                               WHERE ac.project_id = %s
                               AND ac.en_state = 'approved'
                               ORDER BY to_date(ac.technical_field_27607_1, 'DD/MM/YYYY') ASC
                               LIMIT 1;
                               """, (project.id,))
                obj = self.env.cr.fetchone()
                actual_start_timesheet = to_date(obj[1]) if obj else None

                # Ngày bắt đầu thực tế theo dự án
                en_real_start_date = to_date(project.en_real_start_date) if project.en_real_start_date else None

                # ngày ket thuc thực tế
                actual_end = to_date(project.en_real_end_date) if project.en_real_end_date else None
                # Nếu dự án đã đóng và (actual_end rỗng hoặc actual_end < month_start) thì bỏ qua
                if project.stage_id.id == 4 and (not actual_end or actual_end < month_start):
                    continue
                #  Ngày bắt đầu kế hoạch
                self.env.cr.execute("""
                    WITH latest_baseline AS (
                        SELECT DISTINCT ON (e.project_id)
                            e.id, e.project_id, e.state, e.version_type, e.create_date
                        FROM en_wbs e
                        WHERE e.version_type = 'baseline'
                          AND e.project_id = %s
                          AND e.state = 'approved'
                        ORDER BY e.project_id, e.create_date DESC
                    )
                    SELECT x.id, x.en_start_date, x.code
                    FROM project_task x
                    JOIN latest_baseline lb ON x.project_id = lb.project_id
                    WHERE x.project_id = %s
                      AND x.project_wbs_state IN ('approved', 'awaiting')
                      AND x.project_wbs_id = lb.id
                      AND x.category = 'phase'
                      AND x.en_start_date IS NOT NULL
                    ORDER BY x.en_start_date ASC
                    LIMIT 1
                """, (project.id, project.id))

                result = self.env.cr.fetchone()
                plan_start = result[1] if result else None
                day = date(2025,9,1)
                # trường hợp Plan Start Date > 01/09/2025 thì cập nhật en_real_start_date theo timesheet
                if plan_start and plan_start > day:
                    actual_start = actual_start_timesheet
                    if actual_start and actual_start != en_real_start_date:
                        project.write({
                            'en_real_start_date': actual_start
                        })
                else:
                    actual_start = en_real_start_date

                if actual_start and actual_start > start_month:
                    continue
                phase = result[2] if result else None
                #  Ngày kết thúc kế hoạch
                # trường hợp là dự án bảo trì lấy default ngày cuối tháng
                if project.en_list_project_id.id == 2:
                    plan_end = month_end
                    package = None
                else:
                    self.env.cr.execute("""
                                    WITH date_range AS (
                                        SELECT 
                                            (DATE_TRUNC('month', %s) + INTERVAL '1 month' - INTERVAL '1 day')::date AS month_end
                                    ),
                                    latest_baseline AS (
                                      SELECT DISTINCT ON (e.project_id)
                                        e.id, e.project_id, e.state, e.version_type, e.create_date
                                      FROM en_wbs e
                                      WHERE e.version_type = 'baseline'
                                        AND e.project_id = %s
                                        AND e.state = 'approved'
                                      ORDER BY e.project_id, e.create_date DESC
                                    ),
                                    filtered_tasks AS (
                                      SELECT 
                                        pt.id, pt.date_deadline, pt.project_wbs_state, pt.code
                                      FROM project_task pt
                                      JOIN latest_baseline e ON pt.project_id = e.project_id
                                      JOIN date_range dr ON TRUE
                                      WHERE e.id = pt.project_wbs_id
                                        AND pt.project_wbs_state = 'approved'
                                        AND pt.category IN ('package','child_package')
                                        AND pt.date_deadline IS NOT NULL
                                        AND pt.date_deadline <= dr.month_end
                                    )
                                    SELECT * FROM filtered_tasks
                                    ORDER BY date_deadline DESC
                                    LIMIT 1;
                                """, (month_start, project.id))

                    result = self.env.cr.fetchone()
                    plan_end = result[1] if result else month_end
                    package = result[3] if result else None

                #  Ngày kết thúc thực tế
                self.env.cr.execute("""
                    WITH date_range AS (
                        SELECT 
                            DATE_TRUNC('month', %s)::date AS month_start,
                            (DATE_TRUNC('month', %s) + INTERVAL '1 month' - INTERVAL '1 day')::date AS month_end
                    ),
                    latest_baseline AS (
                      SELECT DISTINCT ON (e.project_id)
                        e.id, e.project_id, e.state, e.version_type, e.create_date
                      FROM en_wbs e
                      WHERE e.version_type = 'baseline'
                        AND e.project_id = %s
                        AND e.state = 'approved'
                      ORDER BY e.project_id, e.create_date DESC
                    ),
                    filtered_tasks AS (
                      SELECT 
                        pt.id, pt.actual_end_date, pt.project_wbs_state, pt.date_deadline, pt.stage_id
                      FROM project_task pt
                      JOIN latest_baseline e ON pt.project_id = e.project_id
                      JOIN date_range dr ON TRUE
                      WHERE e.id = pt.project_wbs_id
                        AND pt.project_wbs_state IN ('approved', 'awaiting')
                        AND pt.category IN ( 'package','child_package')
                        AND pt.stage_id != 96
                        AND pt.date_deadline <= dr.month_end
                    )
                    SELECT * FROM filtered_tasks;
                """, (month_start, month_start, project.id))
                results = self.env.cr.fetchall()

                if project_code:
                    target_calculation_date = today
                    actual_end = today
                else:
                    if results:
                        list_actual_end_date = [r[1] for r in results if r[1] is not None]
                        stages = [r[4] for r in results]

                        if any(stage != 100 for stage in stages):
                            if actual_end and month_start <= actual_end <= month_end:
                                pass
                                target_calculation_date = actual_end
                            else:
                                actual_end = month_end
                                target_calculation_date = actual_end
                        elif project.stage_id.id == 4 and actual_end and actual_end >= month_start:
                            if month_start <= actual_end <= month_end:
                                pass
                                target_calculation_date = actual_end
                            else:
                                actual_end = max(list_actual_end_date) if list_actual_end_date else month_end
                                target_calculation_date = month_end
                        else:
                            actual_end = max(list_actual_end_date) if list_actual_end_date else month_end
                            target_calculation_date = month_end

                    else:
                        actual_end = month_end
                        target_calculation_date = month_end

                # 1. Tính % Schedule Achievement
                schedule_achievement = None
                if plan_start and plan_end and actual_start and actual_end:
                    planned_days = (to_date(plan_end) - to_date(plan_start)).days + 1
                    actual_days = (to_date(actual_end) - to_date(actual_start)).days + 1
                    if planned_days > 0:
                        schedule_achievement = round(actual_days / planned_days * 100, 2)

                # 2. Tính % Effort Efficiency Plan v lastupdate
                cumulative_actual = 0.0
                cumulative_plan = 0.0

                effort_efficiency_last = None
                try:
                    summary_env = self.env['project.resource.summary']

                    self.env.cr.execute("""
                        SELECT id FROM project_resource_summary
                        WHERE project_id = %s
                        AND criteria_type = 'actual'
                        AND to_date(month, 'MM/YYYY') <= %s
                    """, [project.id, month_end])
                    actual_line_ids = [r[0] for r in self.env.cr.fetchall()]
                    actual_lines = summary_env.browse(actual_line_ids)

                    self.env.cr.execute("""
                        SELECT id FROM project_resource_summary
                        WHERE project_id = %s
                        AND criteria_type = 'plan'
                        AND to_date(month, 'MM/YYYY') <= %s
                    """, [project.id, month_end])
                    plan_line_ids = [r[0] for r in self.env.cr.fetchall()]
                    plan_lines = summary_env.browse(plan_line_ids)

                    cumulative_actual = round_float(sum(actual_lines.mapped('value')))
                    cumulative_plan = round_float(sum(plan_lines.mapped('value')))
                    if cumulative_plan > 0:
                        effort_efficiency_last = round((cumulative_actual / cumulative_plan) * 100, 2)
                except Exception as e:
                    _logger.warning(f"Error calculating effort_efficiency_last for project {project.name}: {e}")

                # 3. Tính % Effort Efficiency Monthly
                mm_plan = 0.0
                mm_actual = 0.0

                effort_efficiency_monthly = None
                try:
                    month_str_exact = month_start.strftime('%m/%Y')
                    summary_env = self.env['project.resource.summary']

                    monthly_actual = summary_env.search([
                        ('project_id', '=', project.id),
                        ('criteria_type', '=', 'actual'),
                        ('month', '=', month_str_exact)
                    ], limit=1)

                    monthly_plan = summary_env.search([
                        ('project_id', '=', project.id),
                        ('criteria_type', '=', 'plan'),
                        ('month', '=', month_str_exact)
                    ], limit=1)

                    mm_actual = round_float(monthly_actual.value) if monthly_actual else 0.0
                    mm_plan = round_float(monthly_plan.value) if monthly_plan else 0.0

                    if mm_plan > 0:
                        effort_efficiency_monthly = round((mm_actual / mm_plan) * 100, 2)
                except Exception as e:
                    _logger.warning(f"Error calculating effort_efficiency_monthly for project {project.name}: {e}")
                # 4. Ghi nhận báo cáo (dù có hay không có đủ dữ liệu vẫn ghi lại)
                existing_report = self.search([
                    ('project_code', '=', project.en_code or ''),
                    ('report_month', '=', month_start),
                ], limit=1)

                status_map = {
                    'finish': 'Hoàn thành',
                    'doing': 'Đang thực hiện'
                }

                vals = {
                    'project_code': project.en_code or '',
                    'center_name': project.en_department_id.name if project.en_department_id else '',
                    'project_type': project.en_project_type_id.name if project.en_project_type_id else '',
                    'unit_name': project.en_block_id.name if project.en_block_id else '',
                    'project_management': project.user_id.work_email if project.user_id.work_email else '',
                    'project_manager': project.en_project_manager_id.email if project.en_project_manager_id.email else '',
                    'qa_name': project.en_project_qa_id.email if project.en_project_qa_id.email else '',
                    'project_status': status_map.get(project.en_state, ''),
                    'planned_start_date': plan_start,
                    'planned_release_date': plan_end,
                    'package_code': f"{phase}.{package}" if phase and package else phase or package or '',
                    'target_calculation_date': target_calculation_date,
                    'actual_start_date': actual_start,
                    'actual_end_date': actual_end,
                    'planned_effort_month': mm_plan,
                    'actual_effort_month': mm_actual,
                    'planned_effort_cumulative': cumulative_plan,
                    'actual_effort_cumulative': cumulative_actual,
                    'report_month': month_start,
                    'schedule_achievement_last': schedule_achievement,
                    'effort_efficiency_plan_last': effort_efficiency_last,
                    'effort_efficiency_monthly': effort_efficiency_monthly,
                }

                if existing_report:
                    # chỉ update khi có thay đổi
                    updates = {
                        field: val
                        for field, val in vals.items()
                        if existing_report[field] != val
                    }
                    if updates:
                        existing_report.write(updates)
                else:
                    self.create(vals)

