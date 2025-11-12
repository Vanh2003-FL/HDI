from odoo import models, fields, api, _
from odoo.tools.misc import format_date, DEFAULT_SERVER_DATE_FORMAT
from datetime import timedelta, datetime, time
from odoo.tools import config, date_utils, get_lang, html2plaintext
from dateutil.relativedelta import relativedelta
from decimal import localcontext, Decimal, ROUND_HALF_UP
from pytz import timezone
import math
import re


class FinalProjectCompletionQualityWizard(models.TransientModel):
    _name = "final.project.completion.quality.wizard"
    _description = "Báo cáo chi tiết chỉ tiêu cuối dự án"

    # def _default_state_ids(self):
    #     return self.env['project.project.stage'].search([('en_state', 'not in', ['complete', 'cancel'])]).ids

    project_ids = fields.Many2many('project.project', string='Dự án')

    # state_ids = fields.Many2many('project.project.stage', string="Trạng thái", default=lambda self: self._default_state_ids())
    date_from = fields.Date('Từ', required=1)
    date_to = fields.Date('Đến', required=1)
    period = fields.Selection(selection=[
        ('optional', 'Tùy chọn'),
        ('this_month', 'Tháng này'),
        ('this_quarter', 'Quý này'),
        ('this_year', 'Năm nay'),
        ('previous_month', 'Tháng trước'),
        ('previous_quarter', 'Quý trước'),
        ('previous_year', 'Năm trước'),
    ], string='Thời gian đóng dự án', required=1, default='optional')

    @api.onchange('period')
    def onchange_period(self):
        today = fields.Date.today()
        first_day = today.replace(day=1)  # Mùng 1 của tháng hiện tại
        period = self.period
        if period == 'this_month':
            start_date = today.replace(day=1)
            end_date = (today + relativedelta(months=1)).replace(day=1) - relativedelta(days=1)
        elif period == 'this_quarter':
            start_date, end_date = date_utils.get_quarter(today)
        elif period == 'this_year':
            start_date = today.replace(month=1, day=1)
            end_date = today.replace(month=12, day=31)
        elif period == 'previous_month':
            start_date = (today + relativedelta(months=-1)).replace(day=1)
            end_date = today + relativedelta(days=-today.day)
        elif period == 'previous_quarter':
            start_date = (today - relativedelta(months=(today.month - 1) % 3) - relativedelta(months=3)).replace(day=1)
            end_date = today - relativedelta(months=(today.month - 1) % 3) - relativedelta(days=today.day)
        elif period == 'previous_year':
            start_date = (today + relativedelta(years=-1)).replace(day=1, month=1)
            end_date = (today + relativedelta(years=-1)).replace(day=31, month=12)
        else:
            start_date = datetime.strptime(self._context.get('start_date') or first_day.strftime('%Y-%m-%d'), '%Y-%m-%d')
            end_date = datetime.strptime(self._context.get('end_date') or today.strftime('%Y-%m-%d'), '%Y-%m-%d')
        self.date_from = start_date
        self.date_to = end_date

    def do(self):
        self = self.sudo()
        title = "Báo cáo chi tiết chỉ tiêu cuối dự án"

        if self.period and self.period != 'optional' and self.date_from and self.date_to:
            if self.period in ['this_month', 'previous_month']:
                title += f" tháng {self.date_from.month}/{self.date_from.year}"

            elif self.period in ['this_quarter', 'previous_quarter']:
                # Quý này thì lấy đến ngày hiện tại
                end_date = min(fields.Date.today(), self.date_to) if self.period == 'this_quarter' else self.date_to
                title += f" Từ {self.date_from.strftime('%d/%m/%Y')} đến {end_date.strftime('%d/%m/%Y')}"

            elif self.period in ['this_year', 'previous_year']:
                title += f" năm {self.date_from.year}"

            else:
                # fallback (khi có date_from == date_to hoặc case khác)
                if self.date_from == self.date_to:
                    title += f" ngày {self.date_from.strftime('%d/%m/%Y')}"
                else:
                    title += f" từ {self.date_from.strftime('%d/%m/%Y')} đến {self.date_to.strftime('%d/%m/%Y')}"

        action = self.env.ref('ngsc_reporting.action_final_project_completion_quality_report').read()[0]
        action['target'] = 'main'
        action['name'] = f'Báo cáo chi tiết chỉ tiêu cuối dự án'
        action['display_name'] = title
        action['context'] = {'model': 'final.project.completion.quality.report',
                             'project_ids': self.project_ids.ids,
                             # 'state_ids': self.state_ids.ids,
                             'id_popup': self.id,
                             'date_from': self.date_from,
                             'date_to': self.date_to,
                             'period': self.period
                             }
        return action


class FinalProjectCompletionQualityReport(models.AbstractModel):
    _name = "final.project.completion.quality.report"
    _description = "Báo cáo chi tiết chỉ tiêu cuối dự án"
    _inherit = "account.report"

    filter_date = None
    filter_all_entries = None
    filter_journals = None
    filter_analytic = None
    filter_unfold_all = False

    @api.model
    def _get_report_name(self):
        period = self._context.get('period')
        date_from = self._context.get('date_from')
        date_to = self._context.get('date_to')
        today = fields.Date.today()

        title = "Báo cáo chi tiết chỉ tiêu cuối dự án"

        if not period:
            return title

        if date_from:
            date_from = fields.Date.from_string(date_from)
        if date_to:
            date_to = fields.Date.from_string(date_to)

        if period in ['this_month', 'previous_month']:
            title += f" tháng {date_from.month}/{date_from.year}"

        elif period in ['this_quarter', 'previous_quarter']:
            if date_from and date_to:
                if period == 'this_quarter':
                    # Quý này thì lấy đến ngày hiện tại (nếu chưa hết quý)
                    date_to = min(today, date_to)
                title += f" Từ {date_from.strftime('%d/%m/%Y')} đến {date_to.strftime('%d/%m/%Y')}"
            else:
                quarter = (date_from.month - 1) // 3 + 1
                title += f" Quý {quarter}/{date_from.year}"

        elif period in ['this_year', 'previous_year']:
            title += f" năm {date_from.year}"

        elif period == 'optional' and date_from and date_to:
            title += f" từ {date_from.strftime('%d/%m/%Y')} đến {date_to.strftime('%d/%m/%Y')}"

        return title

    def get_report_filename(self, options):
        return f"Báo cáo chi tiết chỉ tiêu cuối dự án"

    def _get_reports_buttons(self, options):
        return [
            # {'name': _('PDF'), 'sequence': 1, 'action': 'print_pdf', 'file_export_type': _('PDF')},
            {'name': _('XLSX'), 'sequence': 2, 'action': 'print_xlsx', 'file_export_type': _('XLSX')},
            {'name': _('Chọn thông tin báo cáo'), 'sequence': 3, 'action': 'get_popup_report'},
        ]

    def get_popup_report(self, options):
        action = self.env['ir.actions.act_window']._for_xml_id(
            'ngsc_reporting.final_project_completion_quality_report_wizard_act')
        action['res_id'] = options.get('id_popup')
        action['name'] = "Báo cáo chi tiết chỉ tiêu cuối dự án"
        return action

    def _get_options(self, previous_options=None):
        res = super()._get_options(previous_options=previous_options)
        lst_key = ['project_ids', 'period', 'id_popup', 'date_from', 'date_to']
        for k in lst_key:
            if k in self._context:
                res[k] = self._context.get(k)
            else:
                res[k] = previous_options.get(k) if previous_options else False
        return res

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
        columns_monthly = []
        columns_details = []

        columns_names = [
            {'name': 'STT', 'rowspan': 2,
             'style': 'padding-left:8px;background-color:#3F4C6A;color:white;text-align: center; white-space:nowrap; border:1px solid #000000'},
            {'name': 'Khối', 'rowspan': 2,
             'style': 'background-color:#3F4C6A;color:white;text-align: center; white-space:nowrap;'},
            {'name': 'Phòng', 'rowspan': 2,
             'style': 'background-color:#3F4C6A;color:white;text-align: center; white-space:nowrap;'},
            {'name': 'Phân loại Dự án', 'rowspan': 2,
             'style': 'min-width:25px;background-color:#3F4C6A;color:white;text-align: center; white-space:nowrap; border:1px solid #000000'},
            {'name': 'Mã dự án', 'rowspan': 2,
             'style': 'background-color:#3F4C6A;color:white;text-align: center; white-space:nowrap; border:1px solid #000000'},
            {'name': 'Quản lý dự án', 'rowspan': 2,
             'style': 'background-color:#3F4C6A;color:white;text-align: center; white-space:nowrap;'},
            {'name': 'Giám đốc dự án', 'rowspan': 2,
             'style': 'background-color:#3F4C6A;color:white;text-align: center; white-space:nowrap;'},
            {'name': 'QA', 'rowspan': 2,
             'style': 'background-color:#3F4C6A;color:white;text-align: center; white-space:nowrap;'},
            {'name': 'Trạng thái dự án', 'rowspan': 2,
             'style': 'background-color:#3F4C6A;color:white;text-align: center; white-space:nowrap;'},
            {'name': 'Schedule Achievement (Ngày)', 'colspan': 6,
             'style': 'background-color:#4768c6;color:white;text-align: center; white-space:nowrap;'},
            # {'name': 'Efffort Efficiency (MM)', 'colspan': 6,'style': 'background-color:#3F4C6A;color:white;text-align: center; white-space:nowrap;'},
            {'name': 'Efffort Efficiency (MM)', 'colspan': 6,
             'style': 'background-color:#B7DFFB;color:black;text-align:center;white-space:nowrap;'},
            # {'name': 'BỘ CHỈ TIÊU CHẤT LƯỢNG DỰ ÁN', 'colspan': 8,'style': 'background-color:#3F4C6A;color:white;text-align: center; white-space:nowrap;'}
            {'name': 'BỘ CHỈ TIÊU CHẤT LƯỢNG DỰ ÁN', 'colspan': 8,
             'style': 'background-color:#3d3440;color:white;text-align:center;white-space:nowrap;'
             }
        ]

        z = 8
        columns_monthly = []
        for name in ['Planned Start Date', 'Plan End date KH 1.0', 'Plan End Date KH 2.0', 'Planned Release Date']:
            z += 1
            columns_monthly += [{'pre-offset': z, 'name': name, 'rowspan': 1,
                                 'style': 'background-color:#f4900a;color:black;text-align:center;white-space:nowrap;'}]

        for name in ['Actual Start Date', 'Actual End Date']:
            z += 1
            columns_monthly += [{'pre-offset': z, 'name': name, 'rowspan': 1,
                                 'style': 'background-color:#fbe2c2;color:black;text-align:center;white-space:nowrap;'}]

        for name in ['Nguồn lực theo BMM đầu tiên', 'Nguồn lực theo BMM được cập nhật mới nhất']:
            z += 1
            columns_monthly += [{'pre-offset': z, 'name': name, 'rowspan': 1,
                                 'style': 'background-color:#F9C4DB;color:black;text-align:center;white-space:nowrap;'}]

        for name in ['Nguồn lực theo Plan v1.0'
            , 'Nguồn lực theo Plan v2.0', 'Nguồn lực theo Plan last update', 'Tổng nguồn lực của dự án']:
            z += 1
            columns_monthly += [{'pre-offset': z, 'name': name, 'rowspan': 1,
                                 'style': 'background-color:#B7DFFB;color:black;text-align:center;white-space:nowrap;'}]

        for name in ['%Schedule Achievement v1.0', '%Schedule Achievement v2.0', '%Schedule Achievement v.lastupdate']:
            z += 1
            columns_monthly += [{'pre-offset': z, 'name': name, 'rowspan': 1,
                                 'style': 'background-color:#fbe2c2;color:black;text-align:center;white-space:nowrap;'}]

        for name in ['% Efffort Efficiency BMM đầu tiên', '% Efffort Efficiency BMM cuối cùng']:
            z += 1
            columns_monthly += [{'pre-offset': z, 'name': name, 'rowspan': 1,
                                 'style': 'background-color:#F9C4DB;color:black;text-align:center;white-space:nowrap;'}]

        for name in ['% Efffort Efficiency Plan v1.0', '% Efffort Efficiency Plan v2.0',
                     '% Efffort Efficiency Plan v lastupdate']:
            z += 1
            columns_monthly += [{'pre-offset': z, 'name': name, 'rowspan': 1,
                                 'style': 'background-color:#B7DFFB;color:black;text-align:center;white-space:nowrap;'}]

        return [columns_names, columns_monthly]

    @api.model
    def _get_lines(self, options, line_id=None):
        norm_map = self._get_norm_map()
        key_map = {
            'schedule_achievement_v1': '%SA1',
            'schedule_achievement_v2': '%SA2',
            'schedule_achievement_last': '%SAL',
            'effort_efficiency_bmm_first': '%EEB1',
            'effort_efficiency_bmm_last': '%EEBL',
            'effort_efficiency_plan_v1': '%EEP1',
            'effort_efficiency_plan_v2': '%EEP2',
            'effort_efficiency_plan_last': '%EEPL',
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

        def format_date(date_val):
            return date_val.strftime('%d/%m/%Y') if date_val else ''

        def safe_color_style( norm_map, key_map, key, value, base_style):
            if value == 0.0:
                return base_style  # Không tô màu norm
            return f"{base_style};{get_color_for_value(norm_map, key_map, key, value)}"

        lines = []

        project_ids = options.get('project_ids')

        background = '#FFFFFF'

        _ext_domain = []
        if project_ids:
            _ext_domain += [('id', 'in', project_ids)]

        _ext_domain += [('stage_id.en_state', 'in', ('complete','finish'))]
        # lọc theo time
        date_from = options.get('date_from')
        date_to = options.get('date_to')

        if date_from and date_to:
            date_from = fields.Date.from_string(date_from)
            date_to = fields.Date.from_string(date_to)
        else:
            date_from = datetime.min.date()
            date_to = datetime.max.date()

        # Bổ sung điều kiện lọc theo closing_date trong khoảng thời gian(chỉ lấy closing_date >= 01/04/2025)
        qualified_reports = self.env['project.completion.quality.report'].search([
            ('closing_date', '!=', False),
            ('closing_date', '>=', max(date_from, datetime(2025, 4, 1).date())),
            ('closing_date', '<=', date_to)
        ])

        qualified_project_codes = qualified_reports.mapped('project_code')

        # Nếu có project_ids được chọn, lọc giao với danh sách trên
        if project_ids:
            _ext_domain += [
                ('id', 'in', project_ids),
                ('en_code', 'in', qualified_project_codes)
            ]
        else:
            _ext_domain += [('en_code', 'in', qualified_project_codes)]


        records = self.env['project.project'].search(_ext_domain)

        with localcontext() as ctx:
            ctx.rounding = ROUND_HALF_UP
            stt_number = 1
            for project in records:
                project_details = self.env['project.completion.quality.report'].sudo().search(
                    [('project_code', '=', project.en_code)])
                # if project_details:
                columns = [
                    # {'name': project.id or '', 'style': f'background-color:{background};vertical-align:middle;text-align: center; white-space:nowrap;border:1px solid #000000'},
                    {'name': project.en_block_id.display_name or '',
                     'style': f'background-color:{background};vertical-align:middle;text-align: center; white-space:nowrap;border:1px solid #000000'},
                    {'name': project.en_department_id.name or '',
                     'style': f'background-color:{background};vertical-align:middle;text-align: center; white-space:nowrap;border:1px solid #000000'},
                    {'name': project.en_project_type_id.name or '',
                     'style': f'background-color:{background};vertical-align:middle;text-align: center; white-space:nowrap;border:1px solid #000000'},
                    {'name': project.en_code or '',
                     'style': f'background-color:{background};vertical-align:middle;text-align: center; white-space:nowrap;border:1px solid #000000'},
                    # {'name': project.user_id.email.replace("@ngs.com.vn", "") or '', 'style': f'background-color:{background};vertical-align:middle;text-align: center; white-space:nowrap;border:1px solid #000000'},
                    {'name': re.sub(r'@.*$', '', project.user_id.email) if project.user_id.email else "",
                     'style': f'background-color:{background};vertical-align:middle;text-align: center; white-space:nowrap;border:1px solid #000000'},

                    # {'name': project.en_project_manager_id.email.replace("@ngs.com.vn", "") or '', 'style': f'background-color:{background};vertical-align:middle;text-align: center; white-space:nowrap;border:1px solid #000000'},
                    {'name': re.sub(r'@.*$', '',
                                    project.en_project_manager_id.email) if project.en_project_manager_id.email else "",
                     'style': f'background-color:{background};vertical-align:middle;text-align: center; white-space:nowrap;border:1px solid #000000'},

                    # {'name': project.en_project_qa_id.email.replace("@ngs.com.vn", "") or '', 'style': f'background-color:{background};vertical-align:middle;text-align: center; white-space:nowrap;border:1px solid #000000'},
                    {'name': re.sub(r'@.*$', '',
                                    project.en_project_qa_id.email) if project.en_project_qa_id.email else "",
                     'style': f'background-color:{background};vertical-align:middle;text-align: center; white-space:nowrap;border:1px solid #000000'},

                    {'name': project.stage_id.display_name or '',
                     'style': f'background-color:{background};vertical-align:middle;text-align: center; white-space:nowrap;border:1px solid #000000'},
                    {'name': format_date(project_details.planned_start_date_last) or '',
                     'style': f'background-color:{background};vertical-align:middle;text-align: center; white-space:nowrap;border:1px solid #000000'},
                    {'name': format_date(project_details.planned_end_date_v1) or '',
                     'style': f'background-color:{background};vertical-align:middle;text-align: center; white-space:nowrap;border:1px solid #000000'},
                    {'name': format_date(project_details.planned_end_date_v2) or '',
                     'style': f'background-color:{background};vertical-align:middle;text-align: center; white-space:nowrap;border:1px solid #000000'},
                    {'name': format_date(project_details.planned_release_date_last) or '',
                     'style': f'background-color:{background};vertical-align:middle;text-align: center; white-space:nowrap;border:1px solid #000000'},
                    {'name': format_date(project_details.actual_start_date) or '',
                     'style': f'background-color:{background};vertical-align:middle;text-align: center; white-space:nowrap;border:1px solid #000000'},
                    {'name': format_date(project_details.actual_end_date) or '',
                     'style': f'background-color:{background};vertical-align:middle;text-align: center; white-space:nowrap;border:1px solid #000000'},
                    {'name': project_details.effort_bmm_first or '',
                     'style': f'background-color:{background};vertical-align:middle;text-align: center; white-space:nowrap;border:1px solid #000000'},
                    {'name': project_details.effort_bmm_last or '',
                     'style': f'background-color:{background};vertical-align:middle;text-align: center; white-space:nowrap;border:1px solid #000000'},
                    {'name': project_details.effort_plan_v1 or '',
                     'style': f'background-color:{background};vertical-align:middle;text-align: center; white-space:nowrap;border:1px solid #000000'},
                    {'name': project_details.effort_plan_v2 or '',
                     'style': f'background-color:{background};vertical-align:middle;text-align: center; white-space:nowrap;border:1px solid #000000'},
                    {'name': project_details.effort_plan_last or '',
                     'style': f'background-color:{background};vertical-align:middle;text-align: center; white-space:nowrap;border:1px solid #000000'},
                    {'name': project_details.effort_total or '',
                     'style': f'background-color:{background};vertical-align:middle;text-align: center; white-space:nowrap;border:1px solid #000000'},

                    {
                        'name': project_details.schedule_achievement_v1 or 'N/A',
                        'style': safe_color_style(
                            norm_map, key_map, 'schedule_achievement_v1',
                            project_details.schedule_achievement_v1,
                            "vertical-align:middle;text-align:center;white-space:nowrap;border:1px solid #000000"
                        )
                    },
                    {
                        'name': project_details.schedule_achievement_v2 or 'N/A',
                        'style': safe_color_style(
                            norm_map, key_map, 'schedule_achievement_v2',
                            project_details.schedule_achievement_v2,
                            "vertical-align:middle;text-align:center;white-space:nowrap;border:1px solid #000000"
                        )
                    },
                    {
                        'name': project_details.schedule_achievement_last or 'N/A',
                        'style': safe_color_style(
                            norm_map, key_map, 'schedule_achievement_last',
                            project_details.schedule_achievement_last,
                            "vertical-align:middle;text-align:center;white-space:nowrap;border:1px solid #000000"
                        )
                    },
                    {
                        'name': project_details.effort_efficiency_bmm_first or 'N/A',
                        'style': safe_color_style(
                            norm_map, key_map, 'effort_efficiency_bmm_first',
                            project_details.effort_efficiency_bmm_first,
                            "vertical-align:middle;text-align:center;white-space:nowrap;border:1px solid #000000"
                        )
                    },
                    {
                        'name': project_details.effort_efficiency_bmm_last or 'N/A',
                        'style': safe_color_style(
                            norm_map, key_map, 'effort_efficiency_bmm_last',
                            project_details.effort_efficiency_bmm_last,
                            "vertical-align:middle;text-align:center;white-space:nowrap;border:1px solid #000000"
                        )
                    },
                    {
                        'name': project_details.effort_efficiency_plan_v1 or 'N/A',
                        'style': safe_color_style(
                            norm_map, key_map, 'effort_efficiency_plan_v1',
                            project_details.effort_efficiency_plan_v1,
                            "vertical-align:middle;text-align:center;white-space:nowrap;border:1px solid #000000"
                        )
                    },
                    {
                        'name': project_details.effort_efficiency_plan_v2 or 'N/A',
                        'style': safe_color_style(
                            norm_map, key_map, 'effort_efficiency_plan_v2',
                            project_details.effort_efficiency_plan_v2,
                            "vertical-align:middle;text-align:center;white-space:nowrap;border:1px solid #000000"
                        )
                    },
                    {
                        'name': project_details.effort_efficiency_plan_last or 'N/A',
                        'style': safe_color_style(
                            norm_map, key_map, 'effort_efficiency_plan_last',
                            project_details.effort_efficiency_plan_last,
                            "vertical-align:middle;text-align:center;white-space:nowrap;border:1px solid #000000"
                        )
                    },

                ]

                lines += [{
                    'id': f'final_project_completion_quality_report_{project.name}',
                    'name': stt_number or '',
                    'style': f'padding-left:8px;background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000',
                    'level': 1,
                    'columns': columns,
                }]
                stt_number += 1
        return lines
