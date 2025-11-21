from odoo import models, fields, api, _, exceptions
from odoo.exceptions import ValidationError

READONLY_STATES = {
    'to_approve': [('readonly', True)],
    'approved': [('readonly', True)],
    'refused': [('readonly', True)],
    'expire': [('readonly', True)],
}

class RecruitmentRequest(models.Model):
    _name = 'hr.recruitment.request'
    _description = 'Yêu cầu tuyển dụng'
    _inherit = 'ngsd.approval'

    name = fields.Char(string='Tên yêu cầu', required=True)
    date_request = fields.Date(string='Ngày đề xuất', default=fields.Date.today)
    employee_id = fields.Many2one("hr.employee", 'Người đề xuất', required=True,  default=lambda self: self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1))
    employee_barcode = fields.Char(string='Mã nhân viên', related='employee_id.barcode', store=True)
    position = fields.Char("Vị trí", related="employee_id.job_title")
    department_id = fields.Many2one("hr.department", related="employee_id.department_id", string="Trung tâm/ban")
    en_department_id = fields.Many2one(comodel_name='en.department', related="employee_id.en_department_id", string="Phòng")
    total_employee = fields.Integer(related="department_id.total_employee", string='Số NV hiện tại', store=True, readonly=True)
    request_type = fields.Selection([
        ('new', 'Theo định biên mới'),
        ('plan', 'Tuyển mới ngoài kế hoạch'),
        ('replace', 'Tuyển thay thế')
    ], string='Loại yêu cầu', default='new')

    replace_employee_ids = fields.Many2many(
        'hr.employee',
        string='Người thay thế'
    )
    recruitment_number = fields.Integer(string='Số lượng tuyển dụng')
    state = fields.Selection([
        ('draft', 'Dự kiến'),
        ('to_approve', 'Chờ duyệt'),
        ('approved', 'Đã duyệt'),
        ('done', 'Hoàn thành'),
        ('refused', 'Từ chối'),
        ('cancel', 'Hủy'),
    ], string='Trạng thái', default='draft')

    approver_id = fields.Many2one(string='Người phê duyệt', states=READONLY_STATES, comodel_name='res.users')

    def button_cancel(self):
        self.state = 'cancel'

    def button_to_approve(self):
        rslt = self.button_sent()
        if not rslt: return
        if self.approver_id: self.send_notify(f'Bạn có yêu cầu tuyển dụng {self.display_name} cần được duyệt', self.approver_id)
        self.write({'state': 'to_approve'})


    job_position = fields.Many2one(comodel_name="hr.job", string="Vị trí tuyển dụng")
    job_quantity = fields.Integer(string="Số lượng tuyển dụng")
    expected_start_date = fields.Date(string="Thời gian đi làm dự kiến")
    en_location_id = fields.Many2one(string='Địa điểm làm việc', comodel_name='hr.work.location')

    currency_id = fields.Many2one("res.currency",
                                  string="Tiền tệ",
                                  default=lambda self: self.env['res.currency'].search([('name', '=', 'VND')], limit=1),
                                  store=True,
                                  required=True)
    expected_salary_from = fields.Monetary(string='Mức lương dự kiến FROM', currency_field='currency_id')
    expected_salary_to = fields.Monetary(string='Mức lương dự kiến TO', currency_field='currency_id')

    gender = fields.Selection([('male', 'Nam'), ('female', 'Nữ')], string="Giới tính")
    # age = fields.Integer(string="Tuổi")
    level_id = fields.Many2one("en.name.level", string='Level')
    # other_requirements = fields.Char(string="Yêu cầu khác")
    foreign_lang = fields.Many2many("hr.recruitment.foreign.lang", string='Trình độ ngoại ngữ')

    years_of_experience = fields.Integer(string="Kinh nghiệm")
    education_level = fields.Selection(string='Trình độ', selection=[
        ('intermediate', 'Trung cấp'),
        ('college', 'Cao đẳng'),
        ('university', 'Đại học'),
        ('master', 'Thạc sĩ'),
        ('doctor', 'Tiến sĩ'),
        ('professor', 'Giáo sư')
    ])
    certificates = fields.Char(string='Chứng chỉ')

    month = fields.Char(string='Tháng',compute='_compute_month_year', store=True)
    year = fields.Char(string='Năm', compute='_compute_month_year', store=True)

    @api.depends('date_request')
    def _compute_month_year(self):
        for rec in self:
            if rec.date_request:
                rec.month = str(rec.date_request.month)
                rec.year = str(rec.date_request.year)
            else:
                rec.month = False
                rec.year = False

    boundary_number = fields.Integer(
        string="Số định biên",
        compute="_compute_boundary_number",
        store=True
    )
    # headcount = fields.Integer(string='Số định biên')

    @api.depends('department_id', 'month', 'year')
    def _compute_boundary_number(self):
        for rec in self:
            domain = [
                ('department_id', '=', rec.department_id.id),
                ('month', '=', rec.month),
                ('year', '=', rec.year),
            ]
            boundary = self.env['hr.boundary'].search(domain, limit=1)
            rec.boundary_number = boundary.hr_boundary if boundary else 0

    # text_description = fields.Html('Mô tả', required=True, tracking=True, copy=True)
    text_job_description = fields.Html(string="Mô tả công việc", tracking=True, copy=True)
    text_job_requirement = fields.Html(string="Yêu cầu công việc", tracking=True, copy=True)
    text_job_benefit = fields.Html(string="Quyền lợi", tracking=True, copy=True)

    hr_id = fields.Many2many(
        "hr.employee",
        "hr_recruitment_request_hr_employee_rel",  # tên bảng trung gian riêng
        "request_id",  # cột tham chiếu tới hr.recruitment.request
        "employee_id",  # cột tham chiếu tới hr.employee
        string="Phân công cho",
        domain="[('en_department_id.code', '=', 'ĐBNL')]"
    )

    @api.onchange("employee_id")
    def _onchange_employee_id(self):
        if self.employee_id and self.employee_id.department_id:
            dept = self.employee_id.department_id
            if dept.talent_acquisition and dept.talent_acquisition not in self.hr_id:
                self.hr_id = [(4, dept.talent_acquisition.id)]

    @api.model
    def create(self, vals):
        # nếu hr_id chưa có trong vals, thì auto gán từ TA
        if not vals.get("hr_id") and vals.get("employee_id"):
            emp = self.env["hr.employee"].browse(vals["employee_id"])
            if emp.department_id and emp.department_id.talent_acquisition:
                vals["hr_id"] = [(6, 0, [emp.department_id.talent_acquisition.id])]
        return super().create(vals)

    def write(self, vals):
        res = super().write(vals)
        for rec in self:
            if "employee_id" in vals and not rec.hr_id:
                dept = rec.employee_id.department_id
                if dept and dept.talent_acquisition:
                    rec.hr_id = [(6, 0, [dept.talent_acquisition.id])]
        return res

    is_manager_hr = fields.Boolean(string="Có quyền trưởng phòng", compute="_compute_is_manager_hr")

    @api.depends()
    def _compute_is_manager_hr(self):
        for rec in self:
            rec.is_manager_hr = self.env.user.has_group('ngsc_recruitment.group_recruitment_request_manager_hr')

    is_proposer = fields.Boolean( string="Là người đề xuất", compute="_compute_is_proposer", store=False )

    @api.depends("employee_id")
    def _compute_is_proposer(self):
        for rec in self:
            rec.is_proposer = bool( rec.employee_id and rec.employee_id.user_id.id == self.env.user.id)
