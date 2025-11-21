import base64
import io

import xlsxwriter
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
from datetime import datetime, date
import math
import logging

from odoo.osv import expression

_logger = logging.getLogger(__name__)


class ProjectCompletionQualityReport(models.Model):
    _name = 'project.completion.quality.report'
    _description = 'Báo cáo chỉ tiêu chất lượng cuối dự án'
    _order = 'center_name'

    unit_name = fields.Char(string='Khối')
    center_name = fields.Char(string='Trung tâm')
    project_type = fields.Char(string='Loại dự án')
    project_code = fields.Char(string='Dự án')
    project_management = fields.Char(string='Quản lý dự án')
    project_manager = fields.Char(string='Giám đốc dự án')
    qa_name = fields.Char(string="QA")
    project_status = fields.Char(string='Trạng thái dự án')
    closing_date = fields.Date(string='Ngày đóng')
    # Thông tin ngày
    planned_start_date_v1 = fields.Date(string='Planned Start Date v1')
    planned_start_date_v2 = fields.Date(string='Planned Start Date v2')
    planned_start_date_last = fields.Date(string='Planned Start Date v last')
    planned_end_date_v1 = fields.Date(string='Plan End Date KH 1.0')
    planned_end_date_v2 = fields.Date(string='Plan End Date KH 2.0')
    planned_release_date_last = fields.Date(string='Planned Release Date KH vlast')
    actual_start_date = fields.Date(string='Actual Start Date')
    actual_end_date = fields.Date(string='Actual End Date')
    # Nguồn lực theo BMM
    effort_bmm_first = fields.Float(string='Nguồn lực theo BMM đầu tiên')
    effort_bmm_last = fields.Float(string='Nguồn lực theo BMM được cập nhật mới nhất')
    # Nguồn lực theo Plan
    effort_plan_v1 = fields.Float(string='Nguồn lực theo Plan v1.0')
    effort_plan_v2 = fields.Float(string='Nguồn lực theo Plan v2.0')
    effort_plan_last = fields.Float(string='Nguồn lực theo Plan last update')
    # Tổng nguồn lực
    effort_total = fields.Float(string='Tổng nguồn lực của dự án')
    # Các chỉ tiêu KPI
    schedule_achievement_v1 = fields.Float(string='% Schedule Achievement v1.0')
    schedule_achievement_v2 = fields.Float(string='% Schedule Achievement v2.0')
    schedule_achievement_last = fields.Float(string='% Schedule Achievement v lastupdate')
    effort_efficiency_bmm_first = fields.Float(string='% Effort Efficiency BMM đầu tiên')
    effort_efficiency_bmm_last = fields.Float(string='% Effort Efficiency BMM cuối cùng')
    effort_efficiency_plan_v1 = fields.Float(string='% Effort Efficiency Plan v1.0')
    effort_efficiency_plan_v2 = fields.Float(string='% Effort Efficiency Plan v2.0')
    effort_efficiency_plan_last = fields.Float(string='% Effort Efficiency Plan v lastupdate')

    @api.model
    def export_excel_report(self, filters):
        domain = []

        if filters.get('months'):
            month_str = filters.get('months')
            if month_str:
                domain.append(('closing_date', 'like', f'{month_str}%'))

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

        # Lấy dữ liệu
        reports = self.search(domain)

        # Tạo file Excel với định dạng
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet("Quality Report")

        # Định nghĩa các style
        header_format = workbook.add_format({
            'bold': True,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#D9D9D9',
            'text_wrap': True  # Cho phép xuống dòng nếu nội dung dài
        })

        cell_format = workbook.add_format({
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True  # Cho phép xuống dòng nếu nội dung dài
        })

        # Header - CORRECTED: Added missing commas between items
        headers = [
            'STT',
            'Khối',
            'Trung tâm',
            'Loại dự án',
            'Mã dự án',
            'Ngày đóng',
            '% Schedule Achievement v1.0',
            '% Schedule Achievement v2.0',
            '% Schedule Achievement v lastupdate',
            '% Effort Efficiency BMM đầu tiên',
            '% Effort Efficiency BMM cuối cùng',
            '% Effort Efficiency Plan v1.0',
            '% Effort Efficiency Plan v2.0',
            '% Effort Efficiency Plan v lastupdate'
        ]

        # Ghi header
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)

        # Ghi dữ liệu và tính toán độ rộng cột tối đa
        max_column_widths = [len(str(header)) for header in headers]  # Khởi tạo bằng độ dài header

        for row_idx, report in enumerate(reports, start=1):
            # Format lại tháng
            closing_date = report.closing_date.strftime('%d/%m/%Y') if report.closing_date else ''

            # Dữ liệu từng dòng - CORRECTED: Make sure this matches headers exactly
            row_data = [
                row_idx,
                report.unit_name or '',
                report.center_name or '',
                report.project_type or '',
                report.project_code or '',
                closing_date,
                report.schedule_achievement_v1 or 0,
                report.schedule_achievement_v2 or 0,
                report.schedule_achievement_last or 0,
                report.effort_efficiency_bmm_first or 0,
                report.effort_efficiency_bmm_last or 0,
                report.effort_efficiency_plan_v1 or 0,
                report.effort_efficiency_plan_v2 or 0,
                report.effort_efficiency_plan_last or 0,
            ]

            # Ghi dữ liệu và cập nhật độ rộng cột tối đa
            for col, data in enumerate(row_data):
                worksheet.write(row_idx, col, data, cell_format)
                # Tính độ dài nội dung (thêm 2 cho padding)
                content_length = len(str(data)) + 2
                if content_length > max_column_widths[col]:
                    max_column_widths[col] = min(content_length, 50)  # Giới hạn tối đa 50 ký tự

        # Đặt độ rộng cột theo nội dung dài nhất
        for col, width in enumerate(max_column_widths):
            # Đặt giới hạn tối thiểu và tối đa cho độ rộng cột
            adjusted_width = max(min(width, 50), 10)
            worksheet.set_column(col, col, adjusted_width)

        worksheet.set_row(0, 20)
        workbook.close()
        output.seek(0)

        return {
            'file_name': 'Bao cáo chỉ tiêu chất lượng cuối dự án.xlsx',
            'file_data': base64.b64encode(output.read()).decode('utf-8')
        }

    @api.model
    def generate_final_project_report(self, project_code=None,  start_month=None,):
        def to_date(val):
            if isinstance(val, datetime):
                return val.date()
            elif isinstance(val, date):
                return val
            elif isinstance(val, str):
                return datetime.strptime(val, "%d/%m/%Y").date()
            return None

        def to_float(val):
            try:
                return float(val)
            except (ValueError, TypeError):
                return 0.0

        def round_float(value, precision=2):
            try:
                return round(float(value), precision)
            except (TypeError, ValueError):
                return 0.0

        today = fields.Date.today()

        if project_code:
            projects = self.env['project.project'].search([('en_code', '=', project_code)])
        else:
            projects = self.env['project.project'].search([('stage_id', '=', 7)])


        # % Schedule Achievement v1.0
        for project in projects:
            # ngay bat dau thuc te
            self.env.cr.execute("""
                            SELECT ac.id, ac.technical_field_27607_1
                            FROM account_analytic_line AS ac
                            WHERE ac.project_id = %s
                            AND ac.en_state = 'approved'
                            ORDER BY to_date(ac.technical_field_27607_1, 'DD/MM/YYYY') ASC
                            LIMIT 1;
                            """, (project.id,))
            obj = self.env.cr.fetchone()
            actual_start = to_date(obj[1]) if obj else None
            en_real_start_date = to_date(project.en_real_start_date)
            if actual_start and actual_start != en_real_start_date:
                project.write({
                    'en_real_start_date': actual_start
                })
            # ngày ket thuc thực tế
            if project_code and not start_month:
                actual_end_old = to_date(project.en_real_end_date) if project.en_real_end_date else None
                actual_end = actual_end_old or today
            elif project_code and start_month:
                actual_end = to_date(project.en_real_end_date) if project.en_real_end_date else None
            else:
                actual_end = to_date(project.en_real_end_date) if project.en_real_end_date else None
            # ngày bắt đầu và ngày kết thúc của phiên bản WBS v1.0
            self.env.cr.execute("""
                SELECT e.id, e.start_date ,e.end_date 
                FROM en_wbs e
                WHERE e.project_id = %s
                  AND e.version_type = 'baseline'
                  AND e.version_number = '1.0'
            """, (project.id,))

            results = self.env.cr.fetchone()
            start_date_v1 = results[1] if results else None
            end_date_v1 = results[2] if results else None

            schedule_achievement_v1 = 0.0
            if actual_start and actual_end and start_date_v1 and end_date_v1:
                actual_duration = (to_date(actual_end) - to_date(actual_start)).days + 1
                planned_duration = (to_date(end_date_v1) - to_date(start_date_v1)).days + 1
                if planned_duration > 0:
                    schedule_achievement_v1 = round(actual_duration / planned_duration * 100, 2)

                # ngày bắt đầu và ngày kết thúc của phiên bản WBS v2.0
            self.env.cr.execute("""
                  SELECT e.id, e.start_date ,e.end_date 
                  FROM en_wbs e
                  WHERE e.project_id = %s
                  AND e.version_type = 'baseline'
                  AND e.index_version = true
                    """, (project.id,))

            results_v2 = self.env.cr.fetchone()
            start_date_v2 = results_v2[1] if results_v2 else start_date_v1
            end_date_v2 = results_v2[2] if results_v2 else end_date_v1

            schedule_achievement_v2 = schedule_achievement_v1
            if actual_start and actual_end and start_date_v2 and end_date_v2:
                actual_durations = (to_date(actual_end) - to_date(actual_start)).days + 1
                planned_durations = (to_date(end_date_v2) - to_date(start_date_v2)).days + 1
                if planned_durations > 0:
                    schedule_achievement_v2 = round(actual_durations / planned_durations * 100, 2)

                # ngày bắt đầu và ngày kết thúc của phiên bản WBS cuối cùng dc duyệt
            self.env.cr.execute("""
                SELECT e.id, e.start_date ,e.end_date 
                FROM en_wbs e
                WHERE e.project_id = %s
                AND e.state = 'approved'
                AND e.version_type = 'baseline'
                ORDER BY e.create_date desc
                LIMIT 1;
                    """, (project.id,))

            obj = self.env.cr.fetchone()
            start_date_last = obj[1] if obj else None
            end_date_last = obj[2] if obj else None

            schedule_achievement_last_update = 0.0
            if actual_start and actual_end and start_date_last and end_date_last:
                actual_day = (to_date(actual_end) - to_date(actual_start)).days + 1
                planned_day = (to_date(end_date_last) - to_date(start_date_last)).days + 1
                if planned_day > 0:
                    schedule_achievement_last_update = round(actual_day / planned_day * 100, 2)

            # Nguồn lực thực tế (MM)

            technical_field_28187_raw = self.env['project.project'].browse(project.id).technical_field_28187
            technical_field_28187 = to_float(technical_field_28187_raw)

            # technical_field_28187 = self.env['project.project'].browse(project.id).technical_field_28187

            en_bmm_project = project.en_bmm
            # Nguồn lực được cấp theo PAKD và QĐTLDA
            effort_efficiency_bmm_first = 0.0
            self.env.cr.execute("""
                              SELECT p.id, p.en_bmm
                              FROM project_decision p
                              WHERE p.project_id = %s
                              AND p.version_type = 'baseline'
                              AND p.version_number = '1.0'
                                """, (project.id,))
            obj = self.env.cr.fetchone()
            en_bmm = round_float(obj[1]) if obj else round_float(en_bmm_project)
            if technical_field_28187 and en_bmm:
                if technical_field_28187 > 0:
                    effort_efficiency_bmm_first = round(technical_field_28187 / en_bmm * 100, 2)

            # Nguồn lực được cấp theo PAKD và QĐTLDA baseline cuối cùng
            effort_efficiency_bmm_last = 0.0
            self.env.cr.execute("""
                 SELECT p.id, p.en_bmm
                 FROM project_decision p
                 WHERE p.project_id = %s
                 AND p.state = 'approved'
                 AND p.version_type = 'baseline'
                 ORDER BY p.create_date desc
                 LIMIT 1;
                     """, (project.id,))
            obj = self.env.cr.fetchone()
            en_bmm_last = round_float(obj[1]) if obj else round_float(en_bmm_project)
            if technical_field_28187 and en_bmm_last:
                if technical_field_28187 > 0:
                    effort_efficiency_bmm_last = round(technical_field_28187 / en_bmm_last * 100, 2)

            # Nguồn lực nội bộ dự án KHNL v1
            effort_efficiency_plan_v1 = 0.0
            self.env.cr.execute("""
                 SELECT en.id, en.en_md
                 FROM en_resource_planning en
                 WHERE en.project_id = %s
                 AND en.version_type = 'baseline'
                 AND en.version_number = '1.0'
                     """, (project.id,))
            obj = self.env.cr.fetchone()
            en_md = obj[1] if obj else None
            mm_rate = project.mm_rate if project.mm_rate else None
            total_mm_v1 = 0
            if en_md and mm_rate:
                if en_md and mm_rate:
                    total_mm = en_md / mm_rate
                    total_mm_v1 = round_float(total_mm)
            if technical_field_28187 and total_mm_v1:
                if technical_field_28187 > 0 and total_mm_v1 > 0:
                    effort_efficiency_plan_v1 = round(technical_field_28187 / total_mm_v1 * 100, 2)

            # Nguồn lực nội bộ dự án KHNL v2
            effort_efficiency_plan_v2 = effort_efficiency_plan_v1
            self.env.cr.execute("""
                WITH ranked AS (
                    SELECT en.id, en.en_md,
                    ROW_NUMBER() OVER (
                        PARTITION BY en.wbs_link_resource_planning 
                        ORDER BY en.create_date DESC
                    ) AS rn
                    FROM en_resource_planning en
                    JOIN en_wbs ew
                        ON en.project_id = ew.project_id
                    WHERE en.project_id = %s
                      AND en.wbs_link_resource_planning = ew.id
                      AND en.version_type = 'baseline'
                      AND ew.version_type = 'baseline'
                      AND ew.index_version = true
                )
                SELECT id, en_md
                FROM ranked
                WHERE rn = 1;
            """, (project.id,))
            obj = self.env.cr.fetchone()
            en_md = obj[1] if obj else None
            mm_rate = project.mm_rate if project.mm_rate else None
            total_mm_v2 = total_mm_v1
            if en_md and mm_rate:
                total_mm = en_md / mm_rate
                total_mm_v2 = round_float(total_mm)
            if technical_field_28187 and total_mm_v2:
                if technical_field_28187 > 0 and total_mm_v2 > 0:
                    effort_efficiency_plan_v2 = round(technical_field_28187 / total_mm_v2 * 100, 2)

            # Nguồn lực nội bộ dự án KHNL cuối cùng
            effort_efficiency_plan_last_update = 0.0
            self.env.cr.execute("""
                 SELECT en.id, en.en_md
                 FROM en_resource_planning en
                 WHERE en.project_id = %s
                 AND en.state = 'approved'
                 AND en.version_type = 'baseline'
                 ORDER BY en.create_date desc
                 LIMIT 1;
                     """, (project.id,))
            obj = self.env.cr.fetchone()
            en_md = obj[1] if obj else None
            mm_rate = project.mm_rate if project.mm_rate else None
            total_mm_plan_last = 0
            if en_md and mm_rate:
                if en_md and mm_rate:
                    total_mm = en_md / mm_rate
                    total_mm_plan_last = round_float(total_mm)
            if technical_field_28187 and total_mm_plan_last:
                if technical_field_28187 > 0 and total_mm_plan_last > 0:
                    effort_efficiency_plan_last_update = round(technical_field_28187 / total_mm_plan_last * 100, 2)

            # Ghi nhận báo cáo (dù có hay không có đủ dữ liệu vẫn ghi lại)
            existing_report = self.search([
                ('project_code', '=', project.en_code or ''),
            ], limit=1)

            status_map = {
                'finish': 'Hoàn thành',
                'complete': 'Đóng'
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
                'closing_date': actual_end,
                'schedule_achievement_v1': schedule_achievement_v1,
                'schedule_achievement_v2': schedule_achievement_v2,
                'schedule_achievement_last': schedule_achievement_last_update,
                'effort_efficiency_bmm_first': effort_efficiency_bmm_first,
                'effort_efficiency_bmm_last': effort_efficiency_bmm_last,
                'effort_efficiency_plan_v1': effort_efficiency_plan_v1,
                'effort_efficiency_plan_v2': effort_efficiency_plan_v2,
                'effort_efficiency_plan_last': effort_efficiency_plan_last_update,

                'planned_start_date_v1': start_date_v1,
                'planned_start_date_v2': start_date_v2,
                'planned_start_date_last': start_date_last,
                'planned_end_date_v1': end_date_v1,
                'planned_end_date_v2': end_date_v2,
                'planned_release_date_last': end_date_last,
                'actual_start_date': actual_start,
                'actual_end_date': actual_end,

                'effort_bmm_first': en_bmm,
                'effort_bmm_last': en_bmm_last,

                'effort_plan_v1': total_mm_v1,
                'effort_plan_v2': total_mm_v2,
                'effort_plan_last': total_mm_plan_last,
                'effort_total': technical_field_28187,
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


    @api.model
    def get_filter_report(self, filters=None):
        filters = filters or {}
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
            prj_code = self.env['project.project'].search([]).mapped('en_code')
            domain.append(('project_code', 'in', prj_code))
        if filters.get('months'):
            month_list = filters['months'] if isinstance(filters['months'], list) else [filters['months']]
            month_domains = []
            for month_str in month_list:
                try:
                    start_date = datetime.strptime(month_str, '%Y-%m').date()
                    end_date = start_date + relativedelta(months=1)  # đầu tháng tiếp theo
                    # tạo domain cho khoảng từ start_date đến trước end_date
                    month_domains.append(['&', ('closing_date', '>=', start_date), ('closing_date', '<', end_date)])
                except ValueError:
                    continue

            if month_domains:
                # Nếu có nhiều tháng, nối OR
                domain += expression.OR(month_domains)
        # ✅ Chặn dự án có closing_date < 01/04/2025
        domain.append(('closing_date', '!=', False))
        domain.append(('closing_date', '>=', datetime(2025, 4, 1).date()))

        # Truy vấn dữ liệu
        records = self.sudo().search_read(domain, [
            'unit_name', 'center_name', 'project_type', 'project_code',
            'closing_date', 'schedule_achievement_v1',
            'effort_efficiency_bmm_first', 'effort_efficiency_bmm_last',
            'schedule_achievement_v2', 'schedule_achievement_last',
            'effort_efficiency_plan_v1', 'effort_efficiency_plan_v2', 'effort_efficiency_plan_last'
        ])
        # ✅ Format closing_date sang dd/mm/YYYY
        for rec in records:
            closing_date = rec.get('closing_date')
            closing_date = rec.get('closing_date')
            if closing_date:
                try:
                    if isinstance(closing_date, datetime):
                        # nếu là datetime.datetime
                        rec['closing_date'] = closing_date.strftime("%d/%m/%Y")
                    elif isinstance(closing_date, date):
                        # nếu là datetime.date
                        rec['closing_date'] = closing_date.strftime("%d/%m/%Y")
                except Exception as e:
                    _logger.warning(f"Lỗi format closing_date {closing_date}: {e}")

        # ==== lấy dữ liệu Norm để JS xử lý vẽ biểu đồ ====
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
            'projects': records,
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
            domain = []

            if month_list:
                or_domain = []
                for month_str in month_list:
                    try:
                        start_date = datetime.strptime(month_str, '%Y-%m').date()
                        end_date = start_date + relativedelta(months=1)

                        or_domain.extend(['&', ('closing_date', '>=', start_date), ('closing_date', '<', end_date)])
                    except Exception:
                        continue

                if or_domain:
                    domain = ['|'] * (len(month_list) - 1) + or_domain

        if filters.get('khoi'):
            domain.append(('unit_name', '=', filters['khoi']))
        if filters.get('center'):
            domain.append(('center_name', '=', filters['center']))
        if filters.get('type'):
            domain.append(('project_type', '=', filters['type']))
        if filters.get('project'):
            project_codes = filters['project'] if isinstance(filters['project'], list) else [filters['project']]
            domain.append(('project_code', 'in', project_codes))

        # ✅ Chặn dự án có closing_date < 01/04/2025
        domain.append(('closing_date', '!=', False))
        domain.append(('closing_date', '>=', datetime(2025, 4, 1).date()))

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
            # ✅ Format closing_date sang dd/mm/YYYY trước khi clean
            'closing_date': clean([
                d.strftime("%d/%m/%Y") if isinstance(d, (date, datetime)) else d
                for d in records.mapped('closing_date') if d
            ]),
            'project_details': project_info,
        }
