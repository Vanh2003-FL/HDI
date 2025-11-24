# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    
    # Basic HDI Fields
    hdi_employee_code = fields.Char(
        string='Mã nhân viên HDI',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        help='Mã nhân viên tự động theo quy tắc HDI'
    )
    
    # Employee Status & Type (From NGSD ngsd_base)
    hdi_status = fields.Selection([
        ('draft', 'Nháp'),
        ('probation', 'Thử việc'),
        ('official', 'Chính thức'),
        ('intern', 'Thực tập'),
        ('contract', 'Hợp đồng'),
        ('consultant', 'Tư vấn'),
        ('inactive', 'Ngừng hoạt động'),
        ('terminated', 'Đã nghỉ việc'),
    ], string='Trạng thái HDI', default='draft', tracking=True)
    
    hdi_employee_type = fields.Selection([
        ('permanent', 'Nhân viên chính thức'),
        ('probation', 'Nhân viên thử việc'),
        ('contract', 'Nhân viên hợp đồng'),
        ('part_time', 'Nhân viên bán thời gian'),
        ('intern', 'Thực tập sinh'),
    ], string='Loại nhân viên', default='probation', required=True)
    
    hdi_onboard_date = fields.Date(
        string='Ngày onboard',
        help='Ngày nhân viên chính thức bắt đầu làm việc'
    )
    
    hdi_probation_end_date = fields.Date(
        string='Ngày kết thúc thử việc',
        compute='_compute_probation_end_date',
        store=True
    )
    
    hdi_contract_type = fields.Selection([
        ('indefinite', 'Không xác định thời hạn'),
        ('definite', 'Xác định thời hạn'),
        ('seasonal', 'Theo mùa vụ'),
    ], string='Loại hợp đồng')
    
    # Education & Experience
    hdi_education_level = fields.Selection([
        ('high_school', 'Trung học phổ thông'),
        ('college', 'Cao đẳng'),
        ('university', 'Đại học'),
        ('master', 'Thạc sĩ'),
        ('doctor', 'Tiến sĩ'),
    ], string='Trình độ học vấn')
    
    hdi_major = fields.Char(string='Chuyên ngành')
    hdi_university = fields.Char(string='Trường đào tạo')
    hdi_graduation_year = fields.Integer(string='Năm tốt nghiệp')
    
    hdi_total_experience = fields.Float(
        string='Tổng số năm kinh nghiệm',
        help='Tổng số năm kinh nghiệm làm việc'
    )
    
    # Skills & Competencies (Relations)
    hdi_skill_ids = fields.One2many(
        'hdi.employee.skill',
        'employee_id',
        string='Kỹ năng'
    )
    
    hdi_competency_ids = fields.One2many(
        'hdi.employee.competency', 
        'employee_id',
        string='Năng lực'
    )
    
    hdi_language_ids = fields.One2many(
        'hdi.employee.language',
        'employee_id', 
        string='Ngoại ngữ'
    )
    
    hdi_evaluation_ids = fields.One2many(
        'hr.evaluation',
        'employee_id',
        string='Đánh giá'
    )
    
    # Organizational Relations (NGSD-based)
    hdi_block_id = fields.Many2one(
        'hdi.block',
        string='Khối',
        related='department_id.hdi_block_id',
        store=True,
        readonly=False
    )
    
    hdi_area_id = fields.Many2one(
        'hdi.area', 
        string='Khu vực'
    )
    
    hdi_level_id = fields.Many2one(
        'hdi.level',
        string='Cấp bậc'
    )
    
    hdi_unit_id = fields.Many2one(
        'hdi.unit',
        string='Đơn vị'
    )
    
    # Additional Personal Information (NGSD fields)
    hdi_identity_card = fields.Char(string='CMND/CCCD')
    hdi_identity_issued_date = fields.Date(string='Ngày cấp CMND/CCCD')
    hdi_identity_issued_place = fields.Char(string='Nơi cấp CMND/CCCD')
    
    hdi_passport_number = fields.Char(string='Số hộ chiếu')
    hdi_passport_issued_date = fields.Date(string='Ngày cấp hộ chiếu')
    hdi_passport_expiry_date = fields.Date(string='Ngày hết hạn hộ chiếu')
    
    hdi_tax_code = fields.Char(string='Mã số thuế')
    hdi_social_insurance_number = fields.Char(string='Số BHXH')
    hdi_health_insurance_number = fields.Char(string='Số BHYT')
    
    # Address Details
    hdi_permanent_address = fields.Text(string='Địa chỉ thường trú')
    hdi_current_address = fields.Text(string='Địa chỉ tạm trú')
    hdi_province_id = fields.Many2one('res.country.state', string='Tỉnh/Thành phố')
    hdi_district = fields.Char(string='Quận/Huyện')
    hdi_ward = fields.Char(string='Phường/Xã')
    
    # Family Information
    hdi_marital_status = fields.Selection([
        ('single', 'Độc thân'),
        ('married', 'Đã kết hôn'),
        ('divorced', 'Ly hôn'),
        ('widowed', 'Góa vợ/chồng'),
    ], string='Tình trạng hôn nhân')
    
    hdi_spouse_name = fields.Char(string='Tên vợ/chồng')
    hdi_spouse_phone = fields.Char(string='SĐT vợ/chồng')
    hdi_spouse_job = fields.Char(string='Nghề nghiệp vợ/chồng')
    hdi_children_count = fields.Integer(string='Số con')
    
    # Emergency Contact
    hdi_emergency_contact_name = fields.Char(string='Người liên hệ khẩn cấp')
    hdi_emergency_contact_phone = fields.Char(string='SĐT khẩn cấp') 
    hdi_emergency_contact_relation = fields.Char(string='Mối quan hệ')
    
    # Health Information
    hdi_blood_type = fields.Selection([
        ('A', 'A'),
        ('B', 'B'), 
        ('AB', 'AB'),
        ('O', 'O'),
    ], string='Nhóm máu')
    
    hdi_health_condition = fields.Text(string='Tình trạng sức khỏe')
    hdi_allergies = fields.Text(string='Dị ứng')
    hdi_disabilities = fields.Text(string='Khuyết tật')
    
    # Career Information
    hdi_career_aspiration = fields.Text(string='Định hướng phát triển')
    hdi_strengths = fields.Text(string='Điểm mạnh')
    hdi_weaknesses = fields.Text(string='Điểm cần cải thiện')
    hdi_hobbies = fields.Text(string='Sở thích')
    
    # Performance & Salary Info
    hdi_performance_level = fields.Selection([
        ('poor', 'Kém'),
        ('below_average', 'Dưới trung bình'),
        ('average', 'Trung bình'),
        ('good', 'Tốt'),
        ('excellent', 'Xuất sắc'),
    ], string='Mức độ hiệu suất')
    
    hdi_salary_level = fields.Selection([
        ('entry', 'Mức cơ bản'),
        ('junior', 'Mức junior'),
        ('middle', 'Mức middle'),
        ('senior', 'Mức senior'), 
        ('lead', 'Mức lead'),
        ('manager', 'Mức quản lý'),
    ], string='Bậc lương')
    
    hdi_last_salary_review = fields.Date(string='Lần xét lương cuối')
    hdi_next_salary_review = fields.Date(string='Lần xét lương tiếp theo')
    
    # Training & Development
    hdi_training_budget = fields.Float(string='Ngân sách đào tạo')
    hdi_training_hours_ytd = fields.Float(string='Giờ đào tạo năm nay')
    hdi_training_target_hours = fields.Float(string='Mục tiêu giờ đào tạo/năm', default=40.0)
    hdi_last_training_date = fields.Date(string='Lần đào tạo cuối')
    
    # Additional Status Fields
    hdi_is_team_leader = fields.Boolean(string='Là team leader')
    hdi_is_key_person = fields.Boolean(string='Nhân sự chủ chốt')
    hdi_is_high_potential = fields.Boolean(string='Nhân tài tiềm năng')
    hdi_retention_risk = fields.Selection([
        ('low', 'Thấp'),
        ('medium', 'Trung bình'),
        ('high', 'Cao'),
    ], string='Rủi ro nghỉ việc')
    
    # Notes
    hdi_internal_notes = fields.Text(string='Ghi chú nội bộ')
    hdi_hr_notes = fields.Text(string='Ghi chú HR')
    
    # Statistics
    hdi_total_leave_days = fields.Float(
        string='Tổng ngày nghỉ phép',
        compute='_compute_leave_stats',
        help='Tổng số ngày nghỉ phép đã sử dụng'
    )
    
    hdi_remaining_leave_days = fields.Float(
        string='Ngày phép còn lại',
        compute='_compute_leave_stats',
        help='Số ngày phép còn lại trong năm'
    )
    
    hdi_total_overtime_hours = fields.Float(
        string='Tổng giờ tăng ca',
        compute='_compute_overtime_stats',
        help='Tổng số giờ làm thêm'
    )
    
    hdi_average_performance_score = fields.Float(
        string='Điểm đánh giá trung bình',
        compute='_compute_performance_score',
        help='Điểm trung bình từ các đợt đánh giá'
    )
    
    # Status
    hdi_is_onboarding = fields.Boolean(
        string='Đang onboarding',
        default=False
    )
    
    hdi_onboarding_progress = fields.Integer(
        string='Tiến độ onboarding (%)',
        default=0
    )

    @api.model
    def create(self, vals):
        """Tự động sinh mã nhân viên HDI"""
        if vals.get('hdi_employee_code', _('New')) == _('New'):
            vals['hdi_employee_code'] = self.env['ir.sequence'].next_by_code('hdi.hr.employee') or _('New')
        return super(HrEmployee, self).create(vals)

    @api.depends('hdi_onboard_date')
    def _compute_probation_end_date(self):
        """Tính ngày kết thúc thử việc (60 ngày)"""
        for employee in self:
            if employee.hdi_onboard_date:
                from datetime import timedelta
                employee.hdi_probation_end_date = employee.hdi_onboard_date + timedelta(days=60)
            else:
                employee.hdi_probation_end_date = False

    def _compute_leave_stats(self):
        """Tính thống kê ngày nghỉ phép"""
        for employee in self:
            leaves = self.env['hr.leave'].search([
                ('employee_id', '=', employee.id),
                ('state', '=', 'validate')
            ])
            employee.hdi_total_leave_days = sum(leaves.mapped('number_of_days'))
            # TODO: Tính ngày phép còn lại dựa trên policy công ty
            employee.hdi_remaining_leave_days = 12 - employee.hdi_total_leave_days

    def _compute_overtime_stats(self):
        """Tính tổng giờ tăng ca"""
        for employee in self:
            # TODO: Implement overtime calculation
            employee.hdi_total_overtime_hours = 0.0

    @api.depends('hdi_evaluation_ids.total_score')
    def _compute_performance_score(self):
        """Tính điểm đánh giá trung bình"""
        for employee in self:
            if employee.hdi_evaluation_ids:
                scores = employee.hdi_evaluation_ids.mapped('total_score')
                employee.hdi_average_performance_score = sum(scores) / len(scores) if scores else 0.0
            else:
                employee.hdi_average_performance_score = 0.0
    
    @api.onchange('hdi_level_id')
    def _onchange_hdi_level_id(self):
        """Tự động cập nhật bậc lương theo cấp bậc"""
        if self.hdi_level_id:
            level_salary_mapping = {
                'intern': 'entry',
                'fresher': 'entry', 
                'junior': 'junior',
                'middle': 'middle',
                'senior': 'senior',
                'leader': 'lead',
                'manager': 'manager',
            }
            if self.hdi_level_id.code in level_salary_mapping:
                self.hdi_salary_level = level_salary_mapping[self.hdi_level_id.code]
    
    @api.onchange('hdi_unit_id')
    def _onchange_hdi_unit_id(self):
        """Tự động cập nhật department và manager theo unit"""
        if self.hdi_unit_id:
            # Tự động gán department nếu unit có department
            if self.hdi_unit_id.department_id:
                self.department_id = self.hdi_unit_id.department_id
            
            # Tự động gán manager nếu unit có manager
            if self.hdi_unit_id.manager_id:
                self.parent_id = self.hdi_unit_id.manager_id
    
    @api.depends('hdi_onboard_date', 'hdi_last_salary_review')
    def _compute_next_salary_review(self):
        """Tính ngày xét lương tiếp theo (6 tháng 1 lần)"""
        for employee in self:
            if employee.hdi_last_salary_review:
                from datetime import timedelta
                employee.hdi_next_salary_review = employee.hdi_last_salary_review + timedelta(days=180)
            elif employee.hdi_onboard_date:
                from datetime import timedelta
                employee.hdi_next_salary_review = employee.hdi_onboard_date + timedelta(days=180)
            else:
                employee.hdi_next_salary_review = False
                
    @api.model
    def _cron_update_salary_reviews(self):
        """Cron job: Nhắc nhở xét lương"""
        from datetime import date, timedelta
        
        # Tìm nhân viên cần xét lương trong 30 ngày tới
        review_date = date.today() + timedelta(days=30)
        employees = self.search([
            ('hdi_next_salary_review', '<=', review_date),
            ('active', '=', True)
        ])
        
        for employee in employees:
            # Tạo activity nhắc nhở
            self.env['mail.activity'].create({
                'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                'res_model_id': self.env.ref('hr.model_hr_employee').id,
                'res_id': employee.id,
                'summary': f'Xét lương cho {employee.name}',
                'note': f'Nhân viên {employee.name} cần được xét lương vào {employee.hdi_next_salary_review}',
                'date_deadline': employee.hdi_next_salary_review,
                'user_id': employee.parent_id.user_id.id if employee.parent_id and employee.parent_id.user_id else self.env.uid,
            })

    @api.constrains('hdi_employee_code')
    def _check_employee_code_unique(self):
        """Kiểm tra mã nhân viên duy nhất"""
        for employee in self:
            if employee.hdi_employee_code != _('New'):
                duplicate = self.search([
                    ('hdi_employee_code', '=', employee.hdi_employee_code),
                    ('id', '!=', employee.id)
                ], limit=1)
                if duplicate:
                    raise ValidationError(_('Mã nhân viên %s đã tồn tại!') % employee.hdi_employee_code)

    def action_start_onboarding(self):
        """Bắt đầu quy trình onboarding"""
        self.ensure_one()
        self.hdi_is_onboarding = True
        self.hdi_onboarding_progress = 0
        return {
            'type': 'ir.actions.act_window',
            'name': _('Onboarding Checklist'),
            'res_model': 'hr.employee.onboarding.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_employee_id': self.id}
        }

    def action_complete_onboarding(self):
        """Hoàn thành onboarding"""
        self.ensure_one()
        if self.hdi_onboarding_progress < 100:
            raise UserError(_('Chưa hoàn thành tất cả các bước onboarding!'))
        self.hdi_is_onboarding = False
        
    def action_convert_to_permanent(self):
        """Chuyển đổi sang nhân viên chính thức"""
        self.ensure_one()
        if self.hdi_employee_type != 'probation':
            raise UserError(_('Chỉ nhân viên thử việc mới có thể chuyển sang chính thức!'))
        self.hdi_employee_type = 'permanent'

    def action_view_evaluations(self):
        """Xem danh sách đánh giá"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Đánh giá nhân viên'),
            'res_model': 'hr.evaluation',
            'view_mode': 'tree,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id}
        }
