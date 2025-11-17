# -*- coding: utf-8 -*-

from odoo import fields, models


class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    hdi_source = fields.Selection([
        ('website', 'Website công ty'),
        ('linkedin', 'LinkedIn'),
        ('facebook', 'Facebook'),
        ('referral', 'Giới thiệu'),
        ('headhunt', 'Headhunt'),
        ('other', 'Khác'),
    ], string='Nguồn ứng viên')
    
    hdi_interview_date = fields.Datetime(string='Ngày phỏng vấn')
    hdi_interview_result = fields.Text(string='Kết quả phỏng vấn')
    hdi_expected_salary = fields.Monetary(
        string='Mức lương mong muốn',
        currency_field='currency_id'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id
    )
