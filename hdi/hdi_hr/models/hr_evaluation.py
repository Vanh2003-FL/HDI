# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrEvaluation(models.Model):
    _name = 'hr.evaluation'
    _description = 'Đánh giá nhân viên'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'evaluation_date desc'

    name = fields.Char(
        string='Tên đánh giá',
        required=True,
        tracking=True
    )
    
    employee_id = fields.Many2one(
        'hr.employee',
        string='Nhân viên',
        required=True,
        tracking=True
    )
    
    department_id = fields.Many2one(
        related='employee_id.department_id',
        string='Phòng ban',
        store=True
    )
    
    job_id = fields.Many2one(
        related='employee_id.job_id',
        string='Vị trí',
        store=True
    )
    
    evaluation_date = fields.Date(
        string='Ngày đánh giá',
        required=True,
        default=fields.Date.context_today,
        tracking=True
    )
    
    evaluation_period = fields.Selection([
        ('monthly', 'Tháng'),
        ('quarterly', 'Quý'),
        ('semi_annual', '6 tháng'),
        ('annual', 'Năm'),
    ], string='Chu kỳ đánh giá', required=True, default='quarterly')
    
    evaluator_id = fields.Many2one(
        'res.users',
        string='Người đánh giá',
        required=True,
        default=lambda self: self.env.user,
        tracking=True
    )
    
    # Criteria scores
    work_quality_score = fields.Integer(
        string='Chất lượng công việc',
        default=0,
        help='Điểm từ 0-100'
    )
    
    productivity_score = fields.Integer(
        string='Năng suất',
        default=0,
        help='Điểm từ 0-100'
    )
    
    teamwork_score = fields.Integer(
        string='Tinh thần làm việc nhóm',
        default=0,
        help='Điểm từ 0-100'
    )
    
    initiative_score = fields.Integer(
        string='Tính chủ động',
        default=0,
        help='Điểm từ 0-100'
    )
    
    discipline_score = fields.Integer(
        string='Kỷ luật',
        default=0,
        help='Điểm từ 0-100'
    )
    
    total_score = fields.Float(
        string='Tổng điểm',
        compute='_compute_total_score',
        store=True,
        tracking=True
    )
    
    rating = fields.Selection([
        ('poor', 'Kém'),
        ('below_average', 'Dưới trung bình'),
        ('average', 'Trung bình'),
        ('good', 'Khá'),
        ('excellent', 'Xuất sắc'),
    ], string='Xếp loại', compute='_compute_rating', store=True)
    
    strengths = fields.Text(string='Điểm mạnh')
    weaknesses = fields.Text(string='Điểm cần cải thiện')
    recommendations = fields.Text(string='Đề xuất')
    
    employee_feedback = fields.Text(string='Phản hồi của nhân viên')
    
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('submitted', 'Đã gửi'),
        ('reviewed', 'Đã xem xét'),
        ('approved', 'Đã phê duyệt'),
        ('cancelled', 'Đã hủy'),
    ], string='Trạng thái', default='draft', tracking=True)
    
    company_id = fields.Many2one(
        'res.company',
        string='Công ty',
        default=lambda self: self.env.company
    )

    @api.depends('work_quality_score', 'productivity_score', 'teamwork_score', 
                 'initiative_score', 'discipline_score')
    def _compute_total_score(self):
        """Tính tổng điểm trung bình"""
        for evaluation in self:
            scores = [
                evaluation.work_quality_score,
                evaluation.productivity_score,
                evaluation.teamwork_score,
                evaluation.initiative_score,
                evaluation.discipline_score,
            ]
            evaluation.total_score = sum(scores) / len(scores) if scores else 0.0

    @api.depends('total_score')
    def _compute_rating(self):
        """Tính xếp loại dựa trên tổng điểm"""
        for evaluation in self:
            if evaluation.total_score >= 90:
                evaluation.rating = 'excellent'
            elif evaluation.total_score >= 75:
                evaluation.rating = 'good'
            elif evaluation.total_score >= 60:
                evaluation.rating = 'average'
            elif evaluation.total_score >= 40:
                evaluation.rating = 'below_average'
            else:
                evaluation.rating = 'poor'

    def action_submit(self):
        """Gửi đánh giá"""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('Chỉ có thể gửi đánh giá ở trạng thái Nháp!'))
        self.state = 'submitted'

    def action_review(self):
        """Xem xét đánh giá"""
        self.ensure_one()
        if self.state != 'submitted':
            raise UserError(_('Chỉ có thể xem xét đánh giá đã gửi!'))
        self.state = 'reviewed'

    def action_approve(self):
        """Phê duyệt đánh giá"""
        self.ensure_one()
        if self.state != 'reviewed':
            raise UserError(_('Chỉ có thể phê duyệt đánh giá đã xem xét!'))
        self.state = 'approved'

    def action_cancel(self):
        """Hủy đánh giá"""
        self.ensure_one()
        self.state = 'cancelled'

    def action_reset_to_draft(self):
        """Đưa về nháp"""
        self.ensure_one()
        self.state = 'draft'
