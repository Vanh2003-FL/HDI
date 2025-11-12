from odoo import fields, models


class ResourceProjectSnapshot(models.Model):
    _name = 'resource.project.snapshot'
    _description = 'Snapshot nhân sự từ dự án'

    resource_decision_id = fields.Many2one('project.decision', string='Bản ghi quyết định', ondelete='cascade')
    project_id = fields.Many2one('project.project', string='Dự án')
    employee_id = fields.Many2one('hr.employee', string='Nhân sự')
    type_id = fields.Many2one('en.type', string='Loại')
    role_ids = fields.Many2many('en.role', 'project_snapshot_role_rel', 'resource_id', 'role_id', string='Vai trò')
    en_job_position_ids = fields.Many2many('en.job.position','project_snapshot_job_position_rel', 'resource_id', 'job_id', string='Vị trí công việc')
    en_state = fields.Selection(string='Trạng thái dự án',
                                selection=[('active', 'Dự kiến'), ('inactive', 'Chờ thực hiện'), ('semi-inactive', 'Nghỉ dài hạn')])
    state = fields.Selection(string='Trạng thái trong dự án',
                                selection=[('active', 'Còn hiệu lực'), ('inactive', 'Hết hiệu lực'),
                                           ('semi-inactive', 'Đang thực hiện')])
    department_id = fields.Many2one('hr.department', string='Bộ phận')
    is_borrow = fields.Boolean(string='Đi mượn')
    date_leave = fields.Date(string='Ngày rời dự án')
    email = fields.Char(string='Email')
    date_start = fields.Date(string='Ngày bắt đầu')
    date_end = fields.Date(string='Ngày kết thúc')
