from odoo import api, fields, models 

class EnQaReportWork(models.Model):
    _name = 'en.qa.report.work'
    _description = 'Kế hoạch công việc QA'

    week = fields.Text('Tuần')
    date = fields.Date('Ngày')
    work_control = fields.Text('Công việc thực hiện/ kiểm soát')
    result_control = fields.Text('Kết quả thực hiện/ kiểm soát')
    note = fields.Text('Note vấn đề')
    workload_use = fields.Text('Workload sử dụng')
    qam_evaluate = fields.Text('QAM đánh giá')
    employee_create_id = fields.Many2one('hr.employee', 'Người tạo bản ghi', related='create_uid.employee_id', store=True)
    product = fields.Text('Sản phẩm')
