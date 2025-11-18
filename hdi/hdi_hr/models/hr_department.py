# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    hdi_department_code = fields.Char(
        string='Mã phòng ban',
        required=True,
        copy=False
    )
    
    hdi_department_type = fields.Selection([
        ('production', 'Sản xuất'),
        ('business', 'Kinh doanh'),
        ('admin', 'Hành chính'),
        ('support', 'Hỗ trợ'),
    ], string='Loại phòng ban', default='admin')
    
    hdi_budget_allocated = fields.Monetary(
        string='Ngân sách phân bổ',
        currency_field='currency_id'
    )
    
    hdi_headcount_plan = fields.Integer(
        string='Kế hoạch biên chế',
        help='Số lượng nhân viên theo kế hoạch'
    )
    
    hdi_headcount_actual = fields.Integer(
        string='Biên chế thực tế',
        compute='_compute_headcount_actual',
        store=True
    )

    # Link to HDI Block
    hdi_block_id = fields.Many2one('hdi.block', string='Khối',
                                   ondelete='set null',
                                   help='Khối liên kết cho phòng ban')
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )

    @api.depends('member_ids')
    def _compute_headcount_actual(self):
        """Tính số lượng nhân viên thực tế"""
        for dept in self:
            dept.hdi_headcount_actual = len(dept.member_ids)
