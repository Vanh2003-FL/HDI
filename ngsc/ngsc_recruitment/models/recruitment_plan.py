from odoo import models, fields, api


class RecruitmentPlan(models.Model):
    _name = "ngsc.recruitment.plan"
    _description = "Kế hoạch tuyển dụng"
    _rec_name = "title"

    title = fields.Char(string="Tên kế hoạch", required=True)
    planning_date = fields.Date(string='Ngày lập kế hoạch', default=fields.Date.today)
    planning_user_id = fields.Many2one('hr.employee',
                                       string='Người lập kế hoạch',
                                       default=lambda self: self.env['hr.employee'].search([('user_id', '=', self.env.user.id)]),
                                       readonly=True, store=True)
    role_user_id = fields.Char(string="Vị trí", related="planning_user_id.job_title", readonly=True, store=True)

    request_id = fields.Many2one('hr.recruitment.request', "Yêu cầu tuyển dụng",
                                 required=True, index=True)
    recruitment_type = fields.Char(string='Loại tuyển dụng')
    source_id = fields.Many2one('utm.source', string='Nguồn tuyển dụng')

    position = fields.Char("Vị trí tuyển dụng", readonly=True, related='request_id.job_position.name')
    date = fields.Date(string='SLA tuyển dụng', required=True)
    department_id = fields.Char(string="Trung tâm/Ban tuyển dụng", readonly=True, related='request_id.department_id.name')
    job_quantity = fields.Integer(string='Số lượng tuyển dụng', readonly=True, related='request_id.job_quantity')
    currency_id = fields.Many2one("res.currency",
                                  string="Tiền tệ",
                                  default=lambda self: self.env['res.currency'].search([('name', '=', 'VND')], limit=1),
                                  store=True,
                                  required=True)
    budget = fields.Monetary(string='Chi phí tuyển dụng', currency_field='currency_id')
    how_to_work = fields.Char(string='Hình thức làm việc')
    experience = fields.Integer(string='Kinh nghiệm', readonly=True, related='request_id.years_of_experience')
    salary_from = fields.Monetary(string='Mức lương từ', currency_field='currency_id', readonly=True, related='request_id.expected_salary_from')
    salary_to = fields.Monetary(string='Mức lương từ', currency_field='currency_id', readonly=True, related='request_id.expected_salary_to')
    gender = fields.Selection([('male', 'Nam'), ('female', 'Nữ')], string="Giới tính", readonly=True, related='request_id.gender')

    council_ids = fields.One2many('ngsc.recruitment.council', 'plan_id', string='Hội đồng tuyển dụng')
    job_description = fields.Html(string='Mô tả công việc', readonly=True, related='request_id.text_job_description')
    job_requirements = fields.Html(string='Yêu cầu công việc', readonly=True, related='request_id.text_job_requirement')
    job_benefit = fields.Html(string='Quyền lợi', readonly=True, related='request_id.text_job_benefit')
    job_note = fields.Html(string='Ghi chú thêm')
    stage = fields.Selection([
        ('draft', 'Kế hoạch'),
        ('recruiting', 'Tuyển dụng'),
        ('done', 'Hoàn thành')
    ], string='Trạng thái', default='draft', tracking=True)
    priority = fields.Selection([
        ('low', 'Thấp'),
        ('normal', 'Trung bình'),
        ('high', 'Cao'),
    ], string='Mức độ ưu tiên', default='normal', tracking=True, required=True)

    @api.onchange('planning_user_id')
    def _onchange_planning_user_id(self):
        user = self.env.user
        domain = []
        if user.has_group('your_module_name.group_hr_recruitment_user'):
            if self.planning_user_id:
                domain = [('hr_id', '=', self.planning_user_id.id)]
        elif user.has_group('your_module_name.group_recruitment_request_manager_hr'):
            domain = []  # No restriction
        return {'domain': {'request_id': domain}}

    def action_recruiting(self):
        for rec in self:
            rec.stage = 'recruiting'

    def action_done(self):
        for rec in self:
            rec.stage = 'done'
