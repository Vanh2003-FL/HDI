from odoo import models, fields, api, _, exceptions
from odoo.exceptions import UserError


class ReportDataHumanResource(models.AbstractModel):
    _name = "report.data.human.resource"
    _description = "Báo cáo Dữ liệu nhân sự"
    _inherit = "account.report"

    @api.model
    def _get_columns(self, options):
        style_color_blue = 'padding-left:8px;background-color:#3472aa;text-align:center;align-items: center; white-space:nowrap; border:1px solid #000000;vertical-align: middle;'
        style_color_orange = 'padding-left:8px;background-color:#ffd966;text-align:center;align-items: center; white-space:nowrap; border:1px solid #000000;vertical-align: middle;'
        style_color_green = 'padding-left:8px;background-color:#8ed26f;text-align:center;align-items: center; white-space:nowrap; border:1px solid #000000;vertical-align: middle;'
        columns_names = [
            {'name': 'STT', 'rowspan': 2, 'style': style_color_blue},
            {'name': 'ID', 'rowspan': 2, 'style': style_color_blue},
            {'name': 'Tình trạng', 'rowspan': 2, 'style': style_color_blue},
            {'name': 'Họ và tên', 'rowspan': 2, 'style': style_color_blue},
            {'name': 'Chức danh', 'rowspan': 2, 'style': style_color_blue},
            {'name': 'Phòng', 'rowspan': 2, 'style': style_color_blue},
            {'name': 'Trung tâm/Ban', 'rowspan': 2, 'style': style_color_blue},
            {'name': 'Khối', 'rowspan': 2, 'style': style_color_blue},
            {'name': 'Khu vực', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Level-Chức vụ', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Ngày vào công ty', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Loại hợp đồng hiện tại', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Lần_HDLD', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Thời hạn hợp đồng hiện tại', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Ngày bắt đầu đào tạo/thực tập/CTV', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Ngày hết đào tạo/thực tập/CTV', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Ngày bắt đầu thử việc', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Ngày hết thử việc', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Ngày hiệu lực HDLD', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Ngày hết hiệu lực HDLD', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'So so BHXH', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Mã số thuế', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Ngày cấp MST', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Nơi cấp MST', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Số người phụ thuộc', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Ngày sinh', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Địa chỉ thường chú', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Nơi ở hiện tại', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'CMND', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Ngày cấp', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Nơi cấp', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Trình độ', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Trường', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Chuyên ngành', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Năm TN', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'CC khac', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Giới tính', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'SDT', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'STK ngân hàng', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Ngân hàng', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Chi nhánh NH', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Email công ty', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Email cá nhân', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Job code', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Level', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Sub-level', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Cấp bậc', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Pay grade', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Bậc lương', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Lương gross offer', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Lương_TV', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Lương cơ bản', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'PC ăn trưa', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'PC đi lại', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'PC điện thoại', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Lương hiệu quả tạm tính', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Total thu nhập mới', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Total thu nhập cũ', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Mức bảo hiểm PTI', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Trạng thái NKL', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Thời gian bắt đầu nghỉ không lương', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Thời gian kết thúc nghỉ không lương', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Trạng thái TS', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Thời gian bắt đầu nghỉ thai sản', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Thời gian kết thúc nghỉ thai sản', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Ngày nghỉ việc', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Ghi chú', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Số', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Thâm niên', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Tháng sinh', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Function', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Site/Dự án', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Role', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Lưu ý', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Tháng nghỉ', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Năm nghỉ', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Tháng onbroad', 'rowspan': 2, 'style': style_color_orange},
            {'name': 'Hồ sơ cá nhân', 'colspan': 10, 'style': style_color_green},
        ]
        comlumns_profile = [
            {'pre-offset': 77, 'name': 'Đơn xin việc', 'style': style_color_green},
            {'name': 'CV', 'style': style_color_green},
            {'name': 'SYLL(*)', 'style': style_color_green},
            {'name': 'GKS', 'style': style_color_green},
            {'name': 'Bằng cấp', 'style': style_color_green},
            {'name': 'Chứng chỉ', 'style': style_color_green},
            {'name': 'CMND', 'style': style_color_green},
            {'name': 'Sổ hộ khẩu', 'style': style_color_green},
            {'name': 'GKSK', 'style': style_color_green},
            {'name': 'Ảnh 3X4', 'style': style_color_green},

        ]
        return [columns_names, comlumns_profile]

    @api.model
    def _get_report_name(self):
        return 'Báo cáo dữ liệu nhân sự'

    def _get_reports_buttons(self, options):
        return [
            {'name': _('XLSX'), 'sequence': 2, 'action': 'print_xlsx', 'file_export_type': _('XLSX')},
        ]

    def format_number(self, number):
        return "{:,}".format(number or 0).replace(',', '.')

    @api.model
    def _get_lines(self, options, line_id=None):
        if not self.env.user.has_group('hr.group_hr_manager'):
            raise UserError('Bạn không được phép xem thông tin này.')
        style_text_align_center = f'padding-left:8px;background-color:#f2f2f2;vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'
        style_text_align_left = f'padding-left:8px;background-color:#f2f2f2;vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'
        lines = []
        self = self.sudo()
        employee = self.env['hr.employee'].search([('is_hidden', '=', False)])
        for idx, employee in enumerate(employee, start=1):
            semi_inactive_day_from = semi_inactive_day_to = maternity_leave_day_from = maternity_leave_day_to = None
            if employee.rest_state == 'semi-inactive':
                semi_inactive_day_from = employee.en_day_layoff_from
                semi_inactive_day_to = employee.en_day_layoff_to
                maternity_leave_day_from = 0
                maternity_leave_day_to = 0
            elif employee.rest_state == 'maternity-leave':
                semi_inactive_day_from = 0
                semi_inactive_day_to = 0
                maternity_leave_day_from = employee.en_day_layoff_from
                maternity_leave_day_to = employee.en_day_layoff_to
            elif employee.rest_state == 'inactive':
                semi_inactive_day_from = employee.en_day_layoff_from
                semi_inactive_day_to = employee.en_day_layoff_to
                maternity_leave_day_from = employee.en_day_layoff_from
                maternity_leave_day_to = employee.en_day_layoff_to

            lines += [{
                'id': f'hr.employee-{employee.id}',
                'name': str(idx), 'style': style_text_align_center,
                'columns': [
                    {'name': employee.barcode or '', 'style': style_text_align_left},
                    {'name': '', 'style': style_text_align_center},
                    {'name': employee.name or '', 'style': style_text_align_left},
                    {'name': employee.job_id.name or '', 'style': style_text_align_left},
                    {'name': employee.en_department_id.name or '', 'style': style_text_align_left},
                    {'name': employee.department_id.name or '', 'style': style_text_align_left},
                    {'name': employee.en_block_id.name or '', 'style': style_text_align_left},
                    {'name': employee.en_area_id.name or '', 'style': style_text_align_left},
                    {'name': '', 'style': style_text_align_left},
                    {'name': employee.en_date_start.strftime('%d/%m/%Y') if employee.en_date_start else '', 'style': style_text_align_center},
                    {'name': employee.contract_id.contract_type_id.name or '', 'style': style_text_align_left},
                    {'name': '', 'style': style_text_align_center},
                    {'name': '', 'style': style_text_align_center},
                    {'name': employee.date_start_training.strftime("%d/%m/%Y") if employee.date_start_training else '', 'style': style_text_align_center},
                    {'name': employee.date_end_training.strftime('%d/%m/%Y') if employee.date_end_training else '', 'style': style_text_align_center},
                    {'name': employee.date_start_probation.strftime('%d/%m/%Y') if employee.date_start_probation else '', 'style': style_text_align_center},
                    {'name': employee.date_end_probation.strftime('%d/%m/%Y') if employee.date_end_probation else '', 'style': style_text_align_center},
                    {'name': employee.contract_id.date_start.strftime('%d/%m/%Y') if employee.contract_id.date_start else '', 'style': style_text_align_center},
                    {'name': employee.contract_id.date_end.strftime('%d/%m/%Y') if employee.contract_id.date_end else '', 'style': style_text_align_center},
                    {'name': employee.notebook_bhxh or '', 'style': style_text_align_center},
                    {'name': employee.tax_code or '', 'style': style_text_align_center},
                    {'name': employee.date_tax.strftime('%d/%m/%Y') if employee.date_tax else '', 'style': style_text_align_center},
                    {'name': employee.place_tax or '', 'style': style_text_align_left},
                    {'name': employee.children or '', 'style': style_text_align_center},
                    {'name': employee.birthday.day if employee.birthday else '', 'style': style_text_align_center},
                    {'name': '', 'style': style_text_align_center},
                    {'name': '', 'style': style_text_align_center},
                    {'name': employee.identification_id or '', 'style': style_text_align_center},
                    {'name': '', 'style': style_text_align_center},
                    {'name': '', 'style': style_text_align_center},
                    {'name': '', 'style': style_text_align_center},
                    {'name': '', 'style': style_text_align_center},
                    {'name': '', 'style': style_text_align_center},
                    {'name': '', 'style': style_text_align_center},
                    {'name': '', 'style': style_text_align_center},
                    {'name': dict(employee.fields_get(['gender'])['gender']['selection']).get(employee.gender or ''), 'style': style_text_align_center},
                    {'name': employee.phone or '', 'style': style_text_align_center},
                    {'name': employee.bank_account_id.acc_number or '', 'style': style_text_align_center},
                    {'name': employee.bank_account_id.bank_id.name or '', 'style': style_text_align_left},
                    {'name': '', 'style': style_text_align_center},
                    {'name': employee.work_email or '', 'style': style_text_align_left},
                    {'name': employee.address_home_id.email or '', 'style': style_text_align_left},
                    {'name': employee.job_code_id.name or '', 'style': style_text_align_left},
                    {'name': employee.level_id.name or '', 'style': style_text_align_left},
                    {'name': employee.sub_level_id.name or '', 'style': style_text_align_left},
                    {'name': employee.en_level_id.name or '', 'style': style_text_align_left},
                    {'name': employee.pay_grade_id.name or '', 'style': style_text_align_left},
                    {'name': employee.salary_grade.name or '', 'style': style_text_align_center},
                    {'name': self.format_number(employee.salary_gross_offer) or '', 'style': style_text_align_center},
                    {'name': self.format_number(employee.salary_probation) or '', 'style': style_text_align_center},
                    {'name': self.format_number(employee.salary_basic) or '', 'style': style_text_align_center},
                    {'name': self.format_number(employee.lunch_allowance) or '', 'style': style_text_align_center},
                    {'name': self.format_number(employee.travel_allowance) or '', 'style': style_text_align_center},
                    {'name': '', 'style': style_text_align_center},
                    {'name': self.format_number(employee.salary_temporary_effective) or '', 'style': style_text_align_center},
                    {'name': self.format_number(employee.total_new_income) or '', 'style': style_text_align_center},
                    {'name': self.format_number(employee.total_old_income) or '', 'style': style_text_align_center},
                    {'name': self.format_number(employee.pti_insurance_level) or '', 'style': style_text_align_center},
                    {'name': '', 'style': style_text_align_center},
                    {'name': semi_inactive_day_from.strftime('%d/%m/%Y') if semi_inactive_day_from else '', 'style': style_text_align_center},
                    {'name': semi_inactive_day_to.strftime('%d/%m/%Y') if semi_inactive_day_to else '', 'style': style_text_align_center},
                    {'name': '', 'style': style_text_align_center},
                    {'name': maternity_leave_day_from.strftime('%d/%m/%Y') if maternity_leave_day_from else '', 'style': style_text_align_center},
                    {'name': maternity_leave_day_to.strftime('%d/%m/%Y') if maternity_leave_day_to else '', 'style': style_text_align_center},
                    {'name': employee.departure_date.strftime('%d/%m/%Y') if employee.departure_date else '', 'style': style_text_align_center},
                    {'name': employee.en_text_off or '', 'style': style_text_align_center},
                    {'name': '', 'style': style_text_align_center},
                    {'name': employee.seniority_date or '', 'style': style_text_align_left},
                    {'name': employee.birthday.month if employee.birthday else '', 'style': style_text_align_center},
                    {'name': '', 'style': style_text_align_center},
                    {'name': '', 'style': style_text_align_center},
                    {'name': '', 'style': style_text_align_center},
                    {'name': '', 'style': style_text_align_center},
                    {'name': '', 'style': style_text_align_center},
                    {'name': '', 'style': style_text_align_center},
                    {'name': '', 'style': style_text_align_center},
                    {'name': '', 'style': style_text_align_center},
                    {'name': '', 'style': style_text_align_center},
                    {'name': '', 'style': style_text_align_center},
                    {'name': '', 'style': style_text_align_center},
                    {'name': '', 'style': style_text_align_center},
                    {'name': '', 'style': style_text_align_center},
                    {'name': '', 'style': style_text_align_center},
                    {'name': '', 'style': style_text_align_center},
                    {'name': '', 'style': style_text_align_center},
                    {'name': '', 'style': style_text_align_center},
                ]
            }]
        return lines

