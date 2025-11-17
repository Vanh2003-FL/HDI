# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # HDI Custom Fields
    hdi_employee_code = fields.Char(
        string='Mã nhân viên HDI',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        help='Mã nhân viên tự động theo quy tắc HDI'
    )
    
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
    
    # Personal Information
    hdi_id_number = fields.Char(string='Số CMND/CCCD')
    hdi_id_issue_date = fields.Date(string='Ngày cấp')
    hdi_id_issue_place = fields.Char(string='Nơi cấp')
    
    hdi_tax_code = fields.Char(string='Mã số thuế')
    hdi_social_insurance_number = fields.Char(string='Số sổ BHXH')
    
    hdi_permanent_address = fields.Text(string='Địa chỉ thường trú')
    hdi_current_address = fields.Text(string='Địa chỉ tạm trú')
    
    # Emergency Contact
    hdi_emergency_contact_name = fields.Char(string='Người liên hệ khẩn cấp')
    hdi_emergency_contact_phone = fields.Char(string='SĐT khẩn cấp')
    hdi_emergency_contact_relation = fields.Char(string='Mối quan hệ')
    
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
    
    hdi_evaluation_ids = fields.One2many(
        'hr.evaluation',
        'employee_id',
        string='Đánh giá'
    )
    
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
