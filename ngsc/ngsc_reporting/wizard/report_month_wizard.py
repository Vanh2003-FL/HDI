from odoo import models, fields, api, _
from datetime import timedelta, date, datetime
from dateutil.relativedelta import relativedelta


class ReportMonthWizard(models.TransientModel):
    _name = "report.month.wizard"
    _description = "Báo cáo chi tiết chỉ tiêu chất lượng dự án hàng tháng"

    report_month = fields.Selection(
        selection=[
            ('01', 'Tháng 1'), ('02', 'Tháng 2'), ('03', 'Tháng 3'), ('04', 'Tháng 4'),
            ('05', 'Tháng 5'), ('06', 'Tháng 6'), ('07', 'Tháng 7'), ('08', 'Tháng 8'),
            ('09', 'Tháng 9'), ('10', 'Tháng 10'), ('11', 'Tháng 11'), ('12', 'Tháng 12'),
        ],
        string="Tháng",
        required=True,
        default=lambda self: (date.today() - relativedelta(months=1)).strftime('%m')
    )

    report_year = fields.Selection(
        selection=lambda self: self._get_year_selection(),
        string="Năm",
        required=True,
        default=lambda self: str(date.today().year)
    )

    project_code = fields.Many2one(
        'report.project.code',
        string='Mã dự án',
        domain=lambda self: [('project_code', 'in', self._get_user_allowed_codes())],
    )

    project_type = fields.Selection(
        selection=lambda self: self._get_project_types(),
        string='Loại dự án'
    )

    def _get_year_selection(self):
        records = self.env['project.quality.monthly.report'].search([('report_month', '!=', False)])
        years = sorted(set(r.report_month.year for r in records if r.report_month), reverse=True)
        return [(str(y), str(y)) for y in years]

    def _get_user_allowed_codes(self):
        allowed_projects = self.env['project.project'].search([])
        return allowed_projects.mapped('en_code')

    def _get_project_types(self):
        codes = self.env['project.project'].search([]).mapped("en_code")
        records = self.env['project.quality.monthly.report'].search([('project_code', 'in', codes)])
        project_types = sorted(set(r.project_type for r in records if r.project_type))
        return [(types, types) for types in project_types]

    def _get_report_month(self):
        codes = self.env['project.project'].search([]).mapped("en_code")
        records = self.env['project.quality.monthly.report'].search([
            ('project_code', 'in', codes)
        ])
        report_months = sorted(
            set(r.report_month for r in records if r.report_month),
            reverse=True
        )
        return report_months[0] if report_months else fields.Date.today()

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(ReportMonthWizard, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu
        )
        if view_type == 'form':
            # Compute dynamic selection và set vào fields info
            allowed_codes = self._get_user_allowed_codes()
            domain = [('project_code', 'in', allowed_codes)]
            res['fields']['project_code']['domain'] = domain
            project_types = self._get_project_types()
            res['fields']['project_type']['selection'] = project_types
        return res

    def run_report(self):
        self = self.sudo()
        report_month_date = datetime.strptime(f"{self.report_year}-{self.report_month}-01", "%Y-%m-%d").date()
        month_str = f"{report_month_date.month}/{report_month_date.year}"
        action = self.env.ref('ngsc_reporting.action_monthly_detailed_quality_report').read()[0]
        action['target'] = 'main'
        action['name'] = f'Báo cáo chi tiết chỉ tiêu chất lượng dự án hàng tháng'
        action['display_name'] = f'Báo cáo chi tiết chỉ tiêu chất lượng dự án tháng {month_str}'
        action['context'] = {
            'model': 'project.report.month',
            'report_month': report_month_date,
            # 'default_report_month': self.report_month.strftime('%Y-%m-%d'),
            'project_code': self.project_code.project_code,
            'project_type': self.project_type,
            'id_popup': self.id,
        }
        return action


class ProjectReportMonthWizard(models.AbstractModel):
    _name = "project.report.month"
    _description = "Báo cáo chi tiết chỉ tiêu chất lượng dự án hàng tháng"
    _inherit = "account.report"

    @api.model
    def _get_report_name(self):
        report_month = self._context.get('report_month')
        if report_month:
            if isinstance(report_month, str):
                report_month = datetime.strptime(report_month, '%Y-%m-%d').date()
            month_str = report_month.strftime('%#m/%Y')
            return f'Báo cáo chi tiết chỉ tiêu chất lượng dự án tháng {month_str}'
        return 'Báo cáo chi tiết chỉ tiêu chất lượng dự án hàng tháng'

    # def get_report_filename(self, options):
    #     return f"Báo cáo chi tiết chỉ tiêu chất lượng dự án hàng tháng"

    def _get_reports_buttons(self, options):
        return [
            {'name': _('XLSX'), 'sequence': 2, 'action': 'print_xlsx', 'file_export_type': _('XLSX'),
             'class': 'btn btn-primary', },
            {'name': _('Chọn thông tin báo cáo'), 'sequence': 3, 'action': 'get_popup_report',
             'class': 'view_report', },
        ]

    def get_popup_report(self, options):
        action = self.env['ir.actions.act_window']._for_xml_id(
            'ngsc_reporting.monthly_detailed_quality_report_wizard_act')
        action['res_id'] = options.get('id_popup')
        return action

    def _get_options(self, previous_options=None):
        res = super()._get_options(previous_options=previous_options)
        context = self._context

        # Lấy report_month từ context để đưa vào options
        if 'report_month' in context:
            res['report_month'] = context['report_month']
        elif previous_options and 'report_month' in previous_options:
            res['report_month'] = previous_options['report_month']
        else:
            res['report_month'] = date.today().replace(day=1).strftime('%Y-%m-%d')

        if context.get('project_code'):
            res['project_code'] = context['project_code']
        if context.get('project_type'):
            res['project_type'] = context['project_type']
        return res

    def _get_report_informations(self, options):
        return {
            'name': 'Báo cáo chi tiết chỉ tiêu chất lượng dự án hàng tháng',
            'report_type': 'general',
            'report_buttons': self._get_reports_buttons(options),
            'options': options,
        }

    def _get_norm_map(self):
        norm_settings = self.env['reporting.norm.setting'].sudo().search_read([], [])
        return {
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

    @api.model
    def _get_columns(self, options):
        style_header = 'background-color:#3F4C6A;color:white;text-align:center;white-space:nowrap;border:1px solid #000000'
        style_sub = 'background-color:#B7DFFB;color:black;text-align:center;white-space:nowrap;border:1px solid #000000'
        style_group_1 = 'background-color:#91D1C2;color:black;text-align:center;white-space:nowrap;border:1px solid #000000'
        style_group_2 = 'background-color:#A9D18E;color:black;text-align:center;white-space:nowrap;border:1px solid #000000'
        style_group_3 = 'background-color:#F4B084;color:black;text-align:center;white-space:nowrap;border:1px solid #000000'

        # Dòng tiêu đề cấp 1 (grouped headers)
        group_header = [
            {'name': '', 'style': style_group_1},  # STT
            {'name': '', 'style': style_group_1},  # Khối
            {'name': '', 'style': style_group_1},  # Đơn vị
            {'name': '', 'style': style_group_1},  # Phân loại
            {'name': '', 'style': style_group_1},  # Mã dự án
            {'name': '', 'style': style_group_1},  # Quản lý DA
            {'name': '', 'style': style_group_1},  # Giám đốc
            {'name': '', 'style': style_group_1},  # QA
            {'name': '', 'style': style_group_1},  # Trạng thái

            {'name': 'Schedule Achievement (Ngày)', 'colspan': 5, 'style': style_group_1},
            {'name': 'Effort Efficiency (MM)', 'colspan': 4, 'style': style_group_2},
            {'name': 'BỘ CHỈ TIÊU CHẤT LƯỢNG DỰ ÁN', 'colspan': 3, 'style': style_group_3},
        ]

        # Dòng tiêu đề cấp 2 (cột chi tiết)
        columns_header = [
            {'name': 'STT', 'style': style_header},
            {'name': 'KHỐI', 'style': style_header},
            {'name': 'Đơn vị', 'style': style_header},
            {'name': 'Phân loại Dự Án', 'style': style_header},
            {'name': 'Mã dự án', 'style': style_header},
            {'name': 'Quản lý dự án', 'style': style_header},
            {'name': 'Giám đốc dự án', 'style': style_header},
            {'name': 'QA', 'style': style_header},
            {'name': 'Trạng thái dự án', 'style': style_header},

            {'name': 'Planned Start Date', 'style': style_sub},
            {'name': 'Planned Release Date KH vlast', 'style': style_sub},
            # {'name': 'Mã gói việc cuối cùng của tháng tính chỉ tiêu', 'style': style_sub},
            {'name': 'Actual Start Date', 'style': style_sub},
            {'name': 'Actual End Date', 'style': style_sub},
            {'name': 'Ngày tính chỉ tiêu', 'style': style_sub},

            {'name': 'Nguồn lực kế hoạch tháng theo KHNL Lastupdate', 'style': style_sub},
            {'name': 'Nguồn lực thực tế trong tháng', 'style': style_sub},
            {'name': 'Nguồn lực kế hoạch TÍCH LŨY theo v.lastUpdate', 'style': style_sub},
            {'name': 'Tổng nguồn lực thực tế TÍCH LŨY', 'style': style_sub},

            {'name': '2.3. %Schedule Achievement v.lastupdate', 'style': style_sub},
            {'name': '3.5. %Effort Efficiency Plan v.lastupdate', 'style': style_sub},
            {'name': '3.5.1. %Effort Efficiency Monthly', 'style': style_sub},
        ]

        return [group_header, columns_header]

    @api.model
    def _get_lines(self, options, line_id=None):
        norm_map = self._get_norm_map()
        key_map = {
            'schedule_achievement_last': '%SAL',
            'effort_efficiency_plan_last': '%EEPL',
            'effort_efficiency_monthly': '%EEM',
        }

        def get_color_for_value(norm_map, key_map, key, value):
            actual_key = key_map.get(key)
            if not actual_key:
                return ''

            norm = norm_map.get(actual_key)
            if not norm:
                return ''

            try:
                value = float(value)
            except (ValueError, TypeError):
                return ''

            target = norm.get('value')
            std_dev = norm.get('std_dev', 0)
            direction = norm.get('direction', 'ge')

            if direction == 'le':
                if value <= (target - std_dev):
                    return f"color:{norm.get('color_good')}"
                elif target >= value > (target - std_dev):
                    return f"color:{norm.get('color_pass')}"
                elif target < value <= (target + std_dev):
                    return f"color:{norm.get('color_fail')}"
                else:
                    return f"color:{norm.get('color_bad')}"
            else:
                if value >= (target + std_dev):
                    return f"color:{norm.get('color_good')}"
                elif target >= value > (target + std_dev):
                    return f"color:{norm.get('color_pass')}"
                elif target > value >= (target - std_dev):
                    return f"color:{norm.get('color_fail')}"
                else:
                    return f"color:{norm.get('color_bad')}"

        def safe_color_style( norm_map, key_map, key, value, base_style):
            if value == 0.0:
                return base_style  # Không tô màu norm
            return f"{base_style};{get_color_for_value(norm_map, key_map, key, value)}"

        lines = []
        style_center = 'vertical-align:middle;text-align: center; white-space:nowrap;border:1px solid #000000'
        style = 'vertical-align:middle; white-space:nowrap;border:1px solid #000000'
        style_left = 'padding-left:8px;background-color:#FFFFFF;vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'

        report_month_str = self.env.context.get('default_report_month') or options.get(
            'report_month') or fields.Date.today().strftime('%Y-%m-01')
        report_month = fields.Date.from_string(report_month_str)

        domain = []
        if report_month:
            first_day = report_month.replace(day=1)
            last_day = (first_day + relativedelta(months=1)) - timedelta(days=1)
            domain.append(('report_month', '>=', first_day))
            domain.append(('report_month', '<=', last_day))

        if options.get('project_code'):
            domain.append(('project_code', 'ilike', options['project_code']))
        if options.get('project_type'):
            domain.append(('project_type', 'ilike', options['project_type']))

        project_codes = self.env['project.project'].search([]).mapped('en_code')
        domain += [('project_code', 'in', project_codes)]

        # Tìm báo cáo theo domain mới (có kiểm quyền)
        reports = self.env['project.quality.monthly.report'].search(domain, order="unit_name, center_name")

        stt = 1
        for report in reports:
            project_managements = report.project_management.split('@')[0]
            project_managers = report.project_manager.split('@')[0]
            qa_names = report.qa_name.split('@')[0]

            columns = [
                {'name': report.unit_name or '', 'style': style},
                {'name': report.center_name or '', 'style': style},
                {'name': report.project_type or '', 'style': style},
                {'name': report.project_code or '', 'style': style},
                {'name': project_managements or '', 'style': style},
                {'name': project_managers or '', 'style': style},
                {'name': qa_names or '', 'style': style},
                {'name': report.project_status or '', 'style': style_center},
                {'name': report.planned_start_date.strftime('%d/%m/%Y') if report.planned_start_date else '',
                 'style': style_center},
                {'name': report.planned_release_date.strftime('%d/%m/%Y') if report.planned_release_date else '',
                 'style': style_center},
                {'name': report.actual_start_date.strftime('%d/%m/%Y') if report.actual_start_date else '',
                 'style': style_center},
                {'name': report.actual_end_date.strftime('%d/%m/%Y') if report.actual_end_date else '',
                 'style': style_center},
                {'name': report.target_calculation_date.strftime('%d/%m/%Y') if report.target_calculation_date else '',
                 'style': style_center},
                {'name': str(report.planned_effort_month or ''), 'style': style_center},
                {'name': str(report.actual_effort_month or ''), 'style': style_center},
                {'name': str(report.planned_effort_cumulative or ''), 'style': style_center},
                {'name': str(report.actual_effort_cumulative or ''), 'style': style_center},
                {
                    'name': f"{report.schedule_achievement_last or 'N/A'}",
                    'style': safe_color_style(norm_map, key_map, 'schedule_achievement_last',
                                                   report.schedule_achievement_last, style_center)
                },
                {
                    'name': f"{report.effort_efficiency_plan_last or 'N/A'}",
                    'style': safe_color_style(norm_map, key_map, 'effort_efficiency_plan_last',
                                                   report.effort_efficiency_plan_last, style_center)
                },
                {
                    'name': f"{report.effort_efficiency_monthly or 'N/A'}",
                    'style': safe_color_style(norm_map, key_map, 'effort_efficiency_monthly',
                                                   report.effort_efficiency_monthly, style_center)
                },
            ]

            lines.append({
                'id': f'report_line_{report.id}',
                'name': stt,
                'columns': columns,
                'style': style_left,
                'level': 1,
            })
            stt += 1

        return lines


class ReportProjectCode(models.Model):
    _name = 'report.project.code'
    _description = 'Mã dự án trong báo cáo chất lượng'
    _auto = False
    _rec_name = 'project_code'

    project_code = fields.Char('Mã dự án', required=True)

    def name_get(self):
        return [(rec.id, rec.project_code) for rec in self]

    @api.model
    def init(self):
        self._cr.execute("""
            CREATE OR REPLACE VIEW report_project_code AS (
                SELECT MIN(id) AS id, project_code
                FROM project_quality_monthly_report
                WHERE project_code IS NOT NULL
                GROUP BY project_code
            )
        """)
