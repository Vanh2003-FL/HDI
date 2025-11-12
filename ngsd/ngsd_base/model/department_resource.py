from odoo import api, fields, models


class EnDepartmentResource(models.Model):
    _name = 'en.department.resource'
    _description = 'Nguồn lực trung tâm'

    employee_id = fields.Many2one('hr.employee', 'Tên nhân sự')
    email = fields.Char('Email', related='employee_id.work_email')
    job_position_id = fields.Many2one('en.job.position', 'Vị trí')
    level_id = fields.Many2one('en.name.level', 'Cấp bậc')
    date_start = fields.Date('Ngày bắt đầu')
    date_end = fields.Date('Ngày kết thúc')
    workload = fields.Float('Workload')
    state = fields.Selection(string="Trạng thái", selection=[
        ('active', 'Đang mượn'),
        ('returned', 'Đã trả'),
        ], required=False, default='active')

    borrow_department_id = fields.Many2one('hr.department', 'Trung tâm mượn/cho mượn')

    department_id = fields.Many2one('hr.department', 'Trung tâm của nhân sự', compute='_compute_department', compute_sudo=True, store=True)
    lender_employee_detail_id = fields.Many2one('en.lender.employee.detail', 'Chi tiết mượn nhân sự')

    @api.depends('employee_id', 'employee_id.department_id')
    def _compute_department(self):
        for rec in self:
            rec.department_id = False
            if rec.employee_id.department_id:
                rec.department_id = rec.employee_id.department_id.id
