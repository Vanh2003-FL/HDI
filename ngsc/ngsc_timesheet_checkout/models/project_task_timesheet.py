from odoo import models, fields, _

# Định nghĩa model mới có tên kỹ thuật là 'project.task.timesheet'
class ProjectTaskTimesheet(models.Model):
    _name = 'project.task.timesheet'  # Tên model, sẽ tạo bảng 'project_task_timesheet' trong database
    _description = 'Project Task Timesheet'  # Mô tả model, dùng hiển thị trong Odoo nếu có dùng view

    # Liên kết với task (nhiệm vụ) trong dự án - bắt buộc phải chọn
    task_id = fields.Many2one(
        'project.task',      # model đích là 'project.task'
        string='Task',       # Nhãn hiển thị trên form
        required=True        # Bắt buộc phải điền trường này
    )

    # Liên kết với người dùng khai timesheet - bắt buộc phải chọn
    user_id = fields.Many2one(
        'res.users',         # model người dùng
        string='User',       # Nhãn hiển thị
        required=True        # Bắt buộc phải điền
    )

    # Mô tả công việc đã làm, có thể để trống
    description = fields.Text(
        string='Description'  # Nhãn hiển thị
    )

    # Số giờ đã làm việc cho task này
    unit_amount = fields.Float(
        string='Hours'        # Nhãn hiển thị là "Hours" (số giờ)
    )

    # Ngày thực hiện task, mặc định là ngày hiện tại theo múi giờ người dùng
    date = fields.Date(
        string='Date',                     # Nhãn hiển thị là "Date"
        default=fields.Date.context_today  # Mặc định là ngày hôm nay (tự động lấy)
    )
