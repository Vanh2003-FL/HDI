import re
from datetime import datetime

from odoo import models, fields, api, _, exceptions
from odoo.exceptions import ValidationError
from odoo.tools.translate import _


class SourcePersonnel(models.Model):
    _name = 'ngsc.recruitment.source.personnel'
    _description = 'Hồ sơ ứng viên'
    _inherit = ['mail.thread.cc', 'mail.activity.mixin', 'utm.mixin']
    _order = 'create_date desc'

    # title = fields.Char(string='Tiêu đề', required=True)
    name = fields.Char('Tên ứng viên', required=True, )
    email = fields.Char('Email', required=True)
    phone = fields.Char('SĐT', required=True)
    en_area_id = fields.Many2one(string='Khu vực', comodel_name='en.name.area')
    block_id = fields.Many2one(comodel_name="en.name.block", string="Khối", domain="[('area_id', '=', en_area_id)]")
    department_id = fields.Many2one(comodel_name="hr.department", string="Trung tâm",
                                    domain="[('block_id', '=', block_id), ('block_id', '!=', False)]")
    en_department_id = fields.Many2one(comodel_name="en.department", string="Phòng ban",
                                       domain="[('department_id', '=', department_id)]")
    job_position = fields.Many2one(comodel_name="hr.job", string="Vị trí ứng tuyển")
    years_of_experience = fields.Integer(string="Số năm kinh nghiệm", required=True, default=1)
    skill_tag = fields.Many2many('ngsc.recruitment.skill.tag',
                                 relation='recruitment_source_personnel__skill_tag_rel',
                                 string="Thẻ kỹ năng", required=True)
    employer_id = fields.Many2one(comodel_name="hr.employee", string="Người tuyển dụng",
                                  required=True, default=lambda self: self.env.user.employee_id)
    source_id = fields.Many2one('utm.source', string="Nguồn tuyển dụng", required=True)
    summary = fields.Text(string='Tóm tắt hồ sơ ứng viên')
    stage_id = fields.Many2one(comodel_name="ngsc.recruitment.source.personnel.stage",
                               copy=False, index=True,
                               ondelete='restrict', tracking=True,
                               store=True, readonly=False,
                               group_expand='_read_group_stage_ids', string='Trạng thái')
    yob = fields.Selection(selection='years_selection', string="Năm sinh", required=True, default='2000')
    gender = fields.Selection(string='Giới tính', selection=[
        ('male', 'Nam'),
        ('female', 'Nữ'),
        ('lesbian', 'Đồng tính nữ'),
        ('gay', 'Đồng tính nam'),
        ('bisexual', 'Song tính'),
        ('transgender', 'Chuyển giới'),
        ('non_binary', 'Phi nhị phân'),
        ('intersex', 'Liên giới tính'),
        ('asexual', 'Vô tính'),
        ('queer', 'Queer'),
        ('questioning', 'Đang trong giai đoạn tìm hiểu bản thân'),
        ('gender_fluid', 'Giới tính không cố định'),
        ('demigirl', 'Người cảm thấy một phần bản thân thuộc về giới nữ'),
        ('demiboy', 'Người cảm thấy một phần bản thân thuộc về giới nam'),
        ('neutrois', 'Trung tính'),
        ('pangender', 'Người trải nghiệm tất cả các giới tính'),
        ('other', 'Khác')
    ], default='other', required=True)
    currency_id = fields.Many2one("res.currency",
                                  string="Tiền tệ",
                                  default=lambda self: self.env['res.currency'].search([('name', '=', 'VND')], limit=1),
                                  required=True)
    salary_expect = fields.Monetary(string='Mức lương kỳ vọng', currency_field='currency_id')
    education_level = fields.Selection(string='Trình độ học vấn', selection=[
        ('intermediate', 'Trung cấp'),
        ('college', 'Cao đẳng'),
        ('university', 'Đại học'),
        ('master', 'Thạc sĩ'),
        ('doctor', 'Tiến sĩ'),
        ('professor', 'Giáo sư')
    ], default='university', required=True)
    major = fields.Char(string='Chuyên ngành')
    certificates = fields.Char(string='Chứng chỉ')
    professional_competence = fields.Char('Năng lực chuyên môn')
    foreign_lang = fields.Char(string='Trình độ ngoại ngữ')
    recent_work = fields.Char(string='Nơi làm việc gần đây')

    news = fields.Many2one(comodel_name='ngsc.news.job', string='Tin tuyển dụng')
    apply_date = fields.Date(string='Ngày nộp hồ sơ')
    can_onboard_date = fields.Date(string='Ngày có thể nhận việc')
    worked_at_company = fields.Boolean(string='Đã từng làm việc tại công ty')

    ref = fields.Many2one(comodel_name='hr.employee', string='Người giới thiệu',
                          relation='ngsc_recruitment_source_personnel__ref')
    department_ref = fields.Char(string="Đơn vị của người giới thiệu", readonly=True)
    email_ref = fields.Char(string='Email của người giới thiệu', readonly=True)
    bonus_ref = fields.Char(string='Thông tin trả thưởng')

    result = fields.Selection(selection=[
        ('pass', 'Đạt'),
        ('fail', 'Chưa đạt'),
    ], string='Kết quả đánh giá')
    resume = fields.Binary(string='Đính kèm CV', attachment=True)
    filename = fields.Char("Filename")

    @api.constrains('file', 'filename')
    def _check_file_type(self):
        for record in self:
            if record.filename:
                if not record.filename.lower().endswith(('.pdf', '.doc', '.docx')):
                    raise ValidationError("Chỉ được phép tải lên file PDF hoặc Word (.doc/.docx).")

    @api.onchange("en_area_id")
    def _onchange_area(self):
        if self.en_area_id:
            self.block_id = False
            self.department_id = False
            self.en_department_id = False

    @api.onchange("block_id")
    def _onchange_block_id(self):
        if self.block_id:
            self.department_id = False
            self.en_department_id = False

    @api.onchange("department_id")
    def _onchange_department_id(self):
        if self.department_id:
            self.en_department_id = False

    @api.onchange("ref")
    def onchange_ref(self):
        if self.ref:
            self.department_ref = self.ref.department_id.name
            self.email_ref = self.ref.work_email

    def years_selection(self):
        year_list = []
        for y in range(datetime.now().year - 80, datetime.now().year - 18):
            year_str = str(y)
            year_list.append((year_str, year_str))
        return year_list

    @api.constrains('years_of_experience')
    def _check_years_of_experience(self):
        for record in self:
            if record.years_of_experience < 1 or record.years_of_experience >= 100:
                raise ValidationError("Số năm kinh nghiệm phải lớn hơn 1 và nhỏ hơn 100.")

    @api.constrains('email')
    def _validate_email(self):
        for record in self:
            match = re.match(r'^[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,4})$', record.email)
            if not match:
                raise ValidationError('Email không đúng định dạng')
            # Tìm các bản ghi có email trùng nhưng không phải bản ghi hiện tại
            existing = self.env['ngsc.recruitment.source.personnel'].search([
                ('email', '=', record.email),
                ('id', '!=', record.id)
            ])
            if existing:
                raise ValidationError(
                    "Email '%s' ứng viên đã tồn tại trên hệ thống, vui lòng kiểm tra lại." % record.email)

    @api.constrains('phone')
    def _validate_phone(self):
        for record in self:
            match = re.match(r"^(0|\+84|84)(3|5|7|8|9)[0-9]{8}$", record.phone)
            if not match:
                raise ValidationError('SĐT không đúng định dạng')

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        stage_obj = self.env['hr.recruitment.stage']
        # Lấy tất cả stage có trong hệ thống
        stage_ids = stage_obj.search([])
        return stage_ids


class SourcePersonnelSearch(models.TransientModel):
    _name = 'ngsc.recruitment.source.personnel.search'
    _description = 'Tìm kiếm hồ sơ ứng viên'

    name = fields.Char(string='Tên')
    en_area_id = fields.Many2one('en.name.area', string='Khu vực')
    block_id = fields.Many2one(comodel_name="en.name.block", string="Khối")
    department_id = fields.Many2one(comodel_name="hr.department", string="Trung tâm")
    en_department_id = fields.Many2one(comodel_name="en.department", string="Phòng ban")
    job_position = fields.Many2one('hr.job', string='Vị trí công việc')
    skill_tag = fields.Many2many('ngsc.recruitment.skill.tag', relation='source_personnel_search__skill_tag',
                                 string='Thẻ kỹ năng')
    years_of_experience = fields.Integer(string='Số năm kinh nghiệm')

    def action_search_personnel(self):
        domain = []
        if self.name:
            domain.append(('name', 'ilike', self.name))
        if self.en_area_id:
            domain.append(('en_area_id', '=', self.en_area_id.id))
        if self.block_id:
            domain.append(('block_id', '=', self.block_id.id))
        if self.department_id:
            domain.append(('department_id', '=', self.department_id.id))
        if self.en_department_id:
            domain.append(('en_department_id', '=', self.en_department_id.id))
        if self.job_position:
            domain.append(('job_position', '=', self.job_position.id))
        if self.skill_tag:
            domain.append(('skill_tag', 'in', self.skill_tag.ids))
        if self.years_of_experience:
            domain.append(('years_of_experience', '>=', self.years_of_experience))

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ngsc.recruitment.source.personnel',
            'view_mode': 'tree,form',
            'views': [(False, 'tree'), (False, 'form')],
            'target': 'current',
            'domain': domain,
        }


class SourcePersonnelStage(models.Model):
    _name = 'ngsc.recruitment.source.personnel.stage'
    _description = 'Giai đoạn hồ sơ nguồn'
    _order = 'sequence'

    name = fields.Char("Tên giai đoạn", required=True)
    sequence = fields.Integer(
        "Thứ tự", default=10,
        help="Gives the sequence order when displaying a list of stages.")
    fold = fields.Boolean(
        "Thu gọn trong kanban",
        help="This stage is folded in the kanban view when there are no records in that stage to display.")
    template_id = fields.Many2one(
        'mail.template', "Mẫu Email",
        help="If set, a message is posted on the applicant using the template when the applicant is set to the stage.")
    legend_blocked = fields.Char(
        'Red Kanban Label', default=lambda self: _('Đã chặn'), required=True)
    legend_done = fields.Char(
        'Green Kanban Label', default=lambda self: _('Sẵn sàng cho giai đoạn kế tiếp'), required=True)
    legend_normal = fields.Char(
        'Grey Kanban Label', default=lambda self: _('Đang thực hiện'), required=True)
    requirements = fields.Text("Yêu cầu")

    @api.constrains('name')
    def _check_unique_name(self):
        for record in self:
            # Tìm các record khác có cùng tên, ngoại trừ record hiện tại
            duplicate = self.search([
                ('name', '=', record.name),
                ('id', '!=', record.id)
            ], limit=1)
            if duplicate:
                raise ValidationError(
                    f"Giai đoạn '{record.name}' đã tồn tại. Vui lòng chọn một tên khác."
                )
