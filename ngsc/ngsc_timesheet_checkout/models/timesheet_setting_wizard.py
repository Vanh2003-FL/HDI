from odoo import models, fields, api

# Wizard dạng tạm dùng để cấu hình việc bật/tắt popup khai Timesheet trước khi checkout
class TimesheetSettingWizard(models.TransientModel):  # TransientModel dùng cho wizard tạm thời
    _name = 'timesheet.setting.wizard'               # Tên model kỹ thuật
    _description = 'Cấu hình bật/tắt popup Timesheet'  # Mô tả dùng để hiển thị trong giao diện

    # Trường boolean để cấu hình có bật popup hay không
    enable_timesheet_popup = fields.Boolean(
        string="Bật khai Timesheet trước khi Checkout"
    )

    @api.model
    def default_get(self, fields_list):
        """
        Ghi đè phương thức default_get để lấy giá trị mặc định từ ir.config_parameter
        và hiển thị đúng trạng thái hiện tại (True/False) của cấu hình popup
        """
        res = super().default_get(fields_list)
        # Đọc cấu hình hiện tại từ bảng ir.config_parameter (dưới quyền sudo)
        param = self.env['ir.config_parameter'].sudo().get_param(
            'ngsc_timesheet_checkout.enable_timesheet_popup'
        )
        # Thiết lập giá trị mặc định của field enable_timesheet_popup theo cấu hình
        res['enable_timesheet_popup'] = param == 'True'
        return res

    def action_save_and_reload(self):
        """
        Phương thức xử lý khi bấm nút Lưu cấu hình.
        Ghi lại giá trị mới vào ir.config_parameter và reload lại giao diện.
        """
        # Ghi giá trị True/False vào cấu hình hệ thống với quyền sudo
        self.env['ir.config_parameter'].sudo().set_param(
            'ngsc_timesheet_checkout.enable_timesheet_popup',
            'True' if self.enable_timesheet_popup else 'False'
        )

        # Reload lại giao diện sau khi lưu
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
