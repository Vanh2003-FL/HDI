# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ResUsers(models.Model):
    _inherit = 'res.users'
    
    # HDI User Extensions for Employee Portal
    hdi_employee_portal_access = fields.Boolean(
        string='Truy cập Portal nhân viên',
        default=True,
        help='Cho phép nhân viên truy cập portal'
    )
    
    hdi_can_view_payslip = fields.Boolean(
        string='Xem phiếu lương',
        default=True,
        help='Nhân viên có thể xem phiếu lương của mình'
    )
    
    hdi_can_request_leave = fields.Boolean(
        string='Yêu cầu nghỉ phép',
        default=True,
        help='Nhân viên có thể tạo đơn nghỉ phép'
    )


class ResCompany(models.Model):
    _inherit = 'res.company'
    
    # HDI Company HR Settings
    hdi_hr_settings_id = fields.Many2one(
        'hdi.hr.settings',
        string='Cấu hình HR HDI'
    )
    
    hdi_working_hours_per_day = fields.Float(
        string='Số giờ làm việc tiêu chuẩn/ngày',
        default=8.0
    )
    
    hdi_working_days_per_week = fields.Float(
        string='Số ngày làm việc/tuần',
        default=5.0
    )
    
    hdi_annual_leave_days = fields.Integer(
        string='Số ngày phép năm',
        default=12,
        help='Số ngày phép năm cơ bản cho nhân viên mới'
    )
    
    hdi_probation_duration = fields.Integer(
        string='Thời gian thử việc (tháng)',
        default=2
    )


class HdiHrSettings(models.Model):
    _name = 'hdi.hr.settings'
    _description = 'HDI HR Settings'
    
    name = fields.Char(string='Tên cấu hình', required=True)
    
    # Attendance Settings
    late_tolerance_minutes = fields.Integer(
        string='Dung sai đi muộn (phút)',
        default=15,
        help='Số phút cho phép đi muộn không bị tính vi phạm'
    )
    
    early_leave_tolerance_minutes = fields.Integer(
        string='Dung sai về sớm (phút)', 
        default=15,
        help='Số phút cho phép về sớm không bị tính vi phạm'
    )
    
    auto_checkout_hours = fields.Integer(
        string='Tự động checkout sau (giờ)',
        default=12,
        help='Tự động checkout nếu quên sau số giờ này'
    )
    
    # Leave Settings
    leave_advance_notice_days = fields.Integer(
        string='Báo trước nghỉ phép (ngày)',
        default=3,
        help='Số ngày tối thiểu phải báo trước khi nghỉ phép'
    )
    
    max_consecutive_leave_days = fields.Integer(
        string='Nghỉ phép liên tục tối đa (ngày)',
        default=10
    )
    
    # Payroll Settings
    payroll_cutoff_day = fields.Integer(
        string='Ngày chốt lương',
        default=25,
        help='Ngày chốt lương trong tháng (1-31)'
    )
    
    overtime_rate_weekday = fields.Float(
        string='Hệ số tăng ca ngày thường',
        default=1.5,
        help='Hệ số tính lương tăng ca ngày thường'
    )
    
    overtime_rate_weekend = fields.Float(
        string='Hệ số tăng ca cuối tuần',
        default=2.0,
        help='Hệ số tính lương tăng ca cuối tuần'
    )
    
    overtime_rate_holiday = fields.Float(
        string='Hệ số tăng ca ngày lễ',
        default=3.0,
        help='Hệ số tính lương tăng ca ngày lễ'
    )
    
    # Recruitment Settings
    cv_retention_days = fields.Integer(
        string='Lưu trữ CV (ngày)',
        default=365,
        help='Số ngày lưu trữ CV của ứng viên'
    )
    
    interview_feedback_required = fields.Boolean(
        string='Bắt buộc feedback phỏng vấn',
        default=True
    )
    
    # Performance Settings
    evaluation_frequency = fields.Selection([
        ('monthly', 'Hàng tháng'),
        ('quarterly', 'Hàng quý'),
        ('semi_annual', '6 tháng/lần'),
        ('annual', 'Hàng năm'),
    ], string='Tần suất đánh giá', default='quarterly')
    
    kpi_weight_technical = fields.Float(
        string='Trọng số KPI kỹ thuật (%)',
        default=40.0
    )
    
    kpi_weight_soft_skill = fields.Float(
        string='Trọng số KPI soft skill (%)',
        default=30.0
    )
    
    kpi_weight_attitude = fields.Float(
        string='Trọng số KPI thái độ (%)',
        default=30.0
    )
    
    @api.constrains('kpi_weight_technical', 'kpi_weight_soft_skill', 'kpi_weight_attitude')
    def _check_kpi_weights(self):
        for record in self:
            total_weight = record.kpi_weight_technical + record.kpi_weight_soft_skill + record.kpi_weight_attitude
            if abs(total_weight - 100.0) > 0.01:
                raise ValidationError(_('Tổng trọng số KPI phải bằng 100%'))


class IrSequence(models.Model):
    _inherit = 'ir.sequence'
    
    @api.model
    def _get_hdi_sequences(self):
        """Tạo các sequence cần thiết cho HDI HR"""
        sequences = [
            ('hdi.employee', 'HDI Employee Code', 'HDI/EMP/', 4),
            ('hdi.contract', 'HDI Contract Code', 'HDI/CT/', 4),
            ('hdi.leave', 'HDI Leave Code', 'HDI/LV/', 4),  
            ('hdi.leave.allocation', 'HDI Leave Allocation Code', 'HDI/AL/', 4),
            ('hdi.evaluation', 'HDI Evaluation Code', 'HDI/EV/', 4),
        ]
        
        for code, name, prefix, padding in sequences:
            if not self.search([('code', '=', code)]):
                self.create({
                    'name': name,
                    'code': code,
                    'prefix': prefix,
                    'padding': padding,
                    'number_next': 1,
                })