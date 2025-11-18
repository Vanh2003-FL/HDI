# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


# Payroll extensions - will be enabled when hr_payroll module is available
# 
# class HrPayslip(models.Model):
#     _inherit = 'hr.payslip'  # Comment out - hr_payroll module may not be available
#
#     # HDI Payslip Extensions  
#     hdi_kpi_bonus = fields.Monetary(string='Thưởng KPI thực tế')
#     hdi_attendance_bonus = fields.Monetary(string='Thưởng chuyên cần')
#     hdi_overtime_bonus = fields.Monetary(string='Thưởng tăng ca')
#
# class HrPayslipRun(models.Model):
#     _inherit = 'hr.payslip.run'  # Comment out - hr_payroll module may not be available
#  
#     # HDI Payslip Batch Extensions
#     hdi_period_type = fields.Selection([...], string='Loại kỳ lương HDI')
#     hdi_approval_status = fields.Selection([...], string='Trạng thái duyệt HDI')


class HdiPayslipDeduction(models.Model):
    _name = 'hdi.payslip.deduction'
    _description = 'HDI Payslip Deductions'
    
    payslip_id = fields.Many2one('hr.payslip', string='Phiếu lương', required=True, ondelete='cascade')
    name = fields.Char(string='Tên khoản trừ', required=True)
    deduction_type = fields.Selection([
        ('late', 'Trừ đi muộn'),
        ('absent', 'Trừ nghỉ không phép'),
        ('advance', 'Trừ tạm ứng'),
        ('insurance', 'Trừ bảo hiểm'),
        ('tax', 'Trừ thuế'),
        ('other', 'Khác'),
    ], string='Loại khoản trừ', required=True)
    amount = fields.Monetary(string='Số tiền', currency_field='currency_id', required=True)
    currency_id = fields.Many2one(related='payslip_id.currency_id', store=True)
    note = fields.Text(string='Ghi chú')