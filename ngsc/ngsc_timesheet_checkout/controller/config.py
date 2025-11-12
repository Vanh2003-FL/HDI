from odoo import http
from odoo.http import request

# Controller định nghĩa route API để lấy cấu hình liên quan đến popup timesheet
class TimesheetConfigController(http.Controller):

    @http.route('/timesheet_checkout/config', type='json', auth='user')
    def get_config(self):
        """
        API được gọi từ client (JS) để kiểm tra xem có bật popup khai báo timesheet khi checkout không.

        Đường dẫn: /timesheet_checkout/config
        Phương thức: JSON-RPC
        Quyền truy cập: yêu cầu người dùng phải đăng nhập (auth='user')

        Trả về:
            {
                'enable_timesheet_popup': True hoặc False
            }
        """
        # Lấy giá trị cấu hình từ bảng ir.config_parameter
        popup_enabled = request.env['ir.config_parameter'].sudo().get_param(
            'ngsc_timesheet_checkout.enable_timesheet_popup'
        )

        # Trả về kết quả dưới dạng boolean (chuỗi 'True' từ config → boolean True)
        return {
            'enable_timesheet_popup': popup_enabled == 'True'
        }
