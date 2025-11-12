from odoo import models, fields

# Khai báo một transient model (dạng popup tạm thời) dùng để cảnh báo người dùng
class TimesheetWarningWizard(models.TransientModel):
    _name = 'timesheet.warning.wizard'  # Tên kỹ thuật của model, sử dụng khi gọi view, context, v.v.
    _description = 'Cảnh báo chưa đủ 8 giờ timesheet'  # Mô tả hiển thị trong UI hoặc dev tools

    # Trường văn bản hiển thị thông báo cảnh báo cho người dùng trong popup
    message = fields.Text(
        default="⚠ Bạn chưa ghi đủ 8 giờ làm việc hôm nay. Bạn muốn làm gì tiếp theo?"
    )

    # Hàm xử lý khi người dùng chọn "Tiếp tục khai timesheet"
    def action_continue_filling(self):
        """
        Mở lại wizard timesheet chính (timesheet.checkout.wizard) để người dùng tiếp tục khai báo.
        """
        return {
            'type': 'ir.actions.act_window',  # Mở một cửa sổ mới (popup)
            'res_model': 'timesheet.checkout.wizard',  # Model cần mở
            'view_mode': 'form',  # Chế độ hiển thị: form
            'view_id': self.env.ref('ngsc_timesheet_checkout.view_timesheet_checkout_wizard_form').id,  # ID của view cần mở
            'target': 'new',  # Mở trong popup (không phải chuyển trang)
        }

    # Hàm xử lý khi người dùng chọn "Bỏ qua và Checkout"
    def action_skip_and_checkout(self):
        """
        Gửi yêu cầu Checkout ngay cả khi chưa đủ 8h, bằng cách gọi lại wizard gốc và thực hiện hành động submit.
        """
        # Lấy ID của wizard timesheet gốc từ context (được truyền vào khi mở warning)
        checkout_wizard_id = self.env.context.get('checkout_wizard_id')

        # Nếu có wizard gốc
        if checkout_wizard_id:
            # Tìm record wizard tương ứng
            wizard = self.env['timesheet.checkout.wizard'].browse(checkout_wizard_id)
            wizard.skip_check = True  # Gán cờ cho biết đã xác nhận bỏ qua kiểm tra 8h
            return wizard.action_submit()  # Gọi hành động submit timesheet

        # Nếu không có wizard (trường hợp lỗi), chỉ reload lại trang
        return {
            'type': 'ir.actions.client',
            'tag': 'reload'
        }
