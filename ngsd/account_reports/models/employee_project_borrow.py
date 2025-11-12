from odoo import models, fields, api, _
from odoo.tools.misc import format_date, DEFAULT_SERVER_DATE_FORMAT
from datetime import timedelta, datetime, time
from odoo.tools import config, date_utils, get_lang, html2plaintext
from dateutil.relativedelta import relativedelta
from decimal import localcontext, Decimal, ROUND_HALF_UP
from pytz import timezone
import math

class EmployeeDepartmentBorrow(models.AbstractModel):
    _name = "employee.department.borrow"
    _description = "Danh sách nhân sự trong dự án của trung tâm khác"
    _inherit = "account.report"

    # filter_date = {'mode': 'range', 'filter': 'this_year'}
    filter_date = None
    filter_all_entries = None
    filter_journals = None
    filter_analytic = None
    filter_unfold_all = None

    @api.model
    def _get_report_name(self):
        ctx = self._context
        return f'''
                     Danh sách nhân sự trong dự án của trung tâm khác
        '''

    def get_report_filename(self, options):
        """The name that will be used for the file when downloading pdf,xlsx,..."""

        return 'Danh sách nhân sự trong dự án của trung tâm khác'

    def _get_reports_buttons(self, options):
        return [
            # {'name': _('PDF'), 'sequence': 1, 'action': 'print_pdf', 'file_export_type': _('PDF')},
            {'name': _('XLSX'), 'sequence': 2, 'action': 'print_xlsx', 'file_export_type': _('XLSX')},
            {'name': _('Lọc dữ liệu'), 'sequence': 3, 'action': 'open_filter'},
        ]

    def open_filter(self, options):
        action = self.env['ir.actions.act_window']._for_xml_id('account_reports.emp_department_borrow_wizard_act')
        action['res_id'] = options.get('id_popup')
        return action

    def _get_options(self, previous_options=None):
        res = super()._get_options(previous_options=previous_options)
        lst_key = ['emp_ids', 'project_ids', 'department_emp_ids', 'department_ids', 'id_popup']
        for k in lst_key:
            if k in self._context:
                res[k] = self._context.get(k)
            else:
                res[k] = previous_options.get(k) if previous_options else False
        return res

    @api.model
    def _get_columns(self, options):
        columns_names = [
            {'name': 'Mã dự án', 'style': 'padding-left:8px;background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap; border:1px solid #000000'},
            {'name': 'Trung tâm dự án', 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Trung tâm của nhân sự', 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Loại nhân sự', 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Tên nhân sự', 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Email', 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Vai trò', 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Vị trí', 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Ngày bắt đầu', 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Ngày kết thúc', 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
            {'name': 'Ngày workload', 'style': 'background-color:#3F4C6A;color:white;text-align:left; white-space:nowrap;'},
        ]
        return [columns_names]

    @api.model
    def _get_lines(self, options, line_id=None):
        lines = []
        self = self.sudo()

        project_ids = options.get('project_ids')
        department_ids = options.get('department_ids')
        department_emp_ids = options.get('department_emp_ids')
        emp_ids = options.get('emp_ids')

        departments = self.env['hr.department'].search([('id', 'in', department_ids)] if department_ids else [])
        projects = self.env['project.project'].search([('id', 'in', project_ids)] if project_ids else [])
        background = '#FFFFFF'

        with localcontext() as ctx:
            ctx.rounding = ROUND_HALF_UP
            for department in departments.sorted(lambda x: x.display_name):
                for project in projects.filtered(lambda x: x.en_department_id == department).sorted(lambda x: x.en_code or ' '):
                    # for resource in project.en_resource_id.order_line.sorted(lambda x: x.employee_id.display_name or ' '):
                    for resource in project.en_resource_id.order_line.filtered(
                        lambda r: (
                                (not department_emp_ids or r.employee_id.department_id.id in department_emp_ids)
                                and (not emp_ids or r.employee_id.id in emp_ids)
                        )
                    ).sorted(lambda r: r.employee_id.display_name or ' '):
                        if resource.employee_id.department_id != department:
                            if background == '#FFFFFF':
                                background = '#D8DAE0'
                            else:
                                background = '#FFFFFF'
                            columns = [
                                {'name': department.display_name, 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                                {'name': resource.employee_id.department_id.display_name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                                {'name': resource.employee_id.en_type_id.display_name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                                {'name': resource.employee_id.display_name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                                {'name': resource.employee_id.work_email or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                                {'name': resource.role_id.display_name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                                {'name': resource.job_position_id.display_name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                                {'name': resource.date_start, 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                                {'name': resource.date_end, 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                                {'name': resource.workload, 'style': f'background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                            ]

                            lines += [{
                                'id': f'project_{project.id}_resource_{resource.id}',
                                'name': project.en_code or '',
                                'style': f'padding-left:8px;background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000',
                                'level': 1,
                                'columns': columns,
                            }]

        return lines
