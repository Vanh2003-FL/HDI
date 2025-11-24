# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class HdiSkill(models.Model):
    """HDI Skills Master"""
    _name = 'hdi.skill'
    _description = 'HDI Skills'
    _order = 'skill_type_id, sequence, name'
    
    name = fields.Char(string='Tên kỹ năng', required=True)
    code = fields.Char(string='Mã kỹ năng')
    sequence = fields.Integer(string='Thứ tự', default=10)
    skill_type_id = fields.Many2one('hdi.skill.type', string='Loại kỹ năng', required=True)
    description = fields.Text(string='Mô tả')
    
    # Skill Categories
    category = fields.Selection([
        ('technical', 'Kỹ năng kỹ thuật'),
        ('soft', 'Kỹ năng mềm'),
        ('management', 'Kỹ năng quản lý'),
        ('language', 'Ngoại ngữ'),
        ('certification', 'Chứng chỉ'),
    ], string='Phân loại', required=True, default='technical')
    
    # Skill Requirements
    is_core_skill = fields.Boolean(string='Kỹ năng cốt lõi', default=False)
    is_leadership_skill = fields.Boolean(string='Kỹ năng lãnh đạo', default=False)
    required_level = fields.Selection([
        ('beginner', 'Cơ bản'),
        ('intermediate', 'Trung bình'),
        ('advanced', 'Nâng cao'),
        ('expert', 'Chuyên gia'),
    ], string='Mức độ yêu cầu tối thiểu')
    
    # Relations
    job_ids = fields.Many2many('hr.job', string='Vị trí công việc yêu cầu')
    employee_skill_ids = fields.One2many('hdi.employee.skill', 'skill_id', string='Nhân viên có kỹ năng')
    employee_count = fields.Integer(string='Số nhân viên có kỹ năng', compute='_compute_employee_count')
    
    active = fields.Boolean(string='Kích hoạt', default=True)
    
    @api.depends('employee_skill_ids')
    def _compute_employee_count(self):
        for skill in self:
            skill.employee_count = len(skill.employee_skill_ids)


class HdiSkillType(models.Model):
    """HDI Skill Types"""
    _name = 'hdi.skill.type'
    _description = 'HDI Skill Types'
    _order = 'sequence, name'
    
    name = fields.Char(string='Tên loại kỹ năng', required=True)
    code = fields.Char(string='Mã loại')
    sequence = fields.Integer(string='Thứ tự', default=10)
    color = fields.Integer(string='Màu', default=0)
    description = fields.Text(string='Mô tả')
    skill_ids = fields.One2many('hdi.skill', 'skill_type_id', string='Kỹ năng')
    skill_count = fields.Integer(string='Số kỹ năng', compute='_compute_skill_count')
    active = fields.Boolean(string='Kích hoạt', default=True)
    
    @api.depends('skill_ids')
    def _compute_skill_count(self):
        for skill_type in self:
            skill_type.skill_count = len(skill_type.skill_ids)


class HdiCompetency(models.Model):
    """HDI Competency Framework"""
    _name = 'hdi.competency'
    _description = 'HDI Competency'
    _order = 'competency_type_id, sequence, name'
    _parent_store = True
    
    name = fields.Char(string='Tên năng lực', required=True)
    code = fields.Char(string='Mã năng lực')
    sequence = fields.Integer(string='Thứ tự', default=10)
    competency_type_id = fields.Many2one('hdi.competency.type', string='Loại năng lực', required=True)
    
    # Hierarchy
    parent_id = fields.Many2one('hdi.competency', string='Năng lực cha')
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many('hdi.competency', 'parent_id', string='Năng lực con')
    
    # Competency Details
    description = fields.Text(string='Mô tả')
    behavioral_indicators = fields.Text(string='Chỉ số hành vi')
    
    # Levels Definition
    level_1_desc = fields.Text(string='Mô tả mức 1')
    level_2_desc = fields.Text(string='Mô tả mức 2')
    level_3_desc = fields.Text(string='Mô tả mức 3')
    level_4_desc = fields.Text(string='Mô tả mức 4')
    level_5_desc = fields.Text(string='Mô tả mức 5')
    
    # Weight & Importance
    weight = fields.Float(string='Trọng số (%)', default=100.0)
    is_core_competency = fields.Boolean(string='Năng lực cốt lõi', default=False)
    is_leadership_competency = fields.Boolean(string='Năng lực lãnh đạo', default=False)
    
    # Relations
    job_ids = fields.Many2many('hr.job', string='Vị trí công việc yêu cầu')
    employee_competency_ids = fields.One2many('hdi.employee.competency', 'competency_id', string='Nhân viên đánh giá')
    employee_count = fields.Integer(string='Số nhân viên đánh giá', compute='_compute_employee_count')
    
    active = fields.Boolean(string='Kích hoạt', default=True)
    
    @api.depends('employee_competency_ids')
    def _compute_employee_count(self):
        for competency in self:
            competency.employee_count = len(competency.employee_competency_ids)


class HdiCompetencyType(models.Model):
    """HDI Competency Types"""
    _name = 'hdi.competency.type'
    _description = 'HDI Competency Types'
    _order = 'sequence, name'
    
    name = fields.Char(string='Tên loại năng lực', required=True)
    code = fields.Char(string='Mã loại')
    sequence = fields.Integer(string='Thứ tự', default=10)
    color = fields.Integer(string='Màu', default=0)
    description = fields.Text(string='Mô tả')
    competency_ids = fields.One2many('hdi.competency', 'competency_type_id', string='Năng lực')
    competency_count = fields.Integer(string='Số năng lực', compute='_compute_competency_count')
    active = fields.Boolean(string='Kích hoạt', default=True)
    
    @api.depends('competency_ids')
    def _compute_competency_count(self):
        for competency_type in self:
            competency_type.competency_count = len(competency_type.competency_ids)


class HdiSkillAssessment(models.Model):
    """HDI Skill Assessments"""
    _name = 'hdi.skill.assessment'
    _description = 'HDI Skill Assessment'
    _order = 'assessment_date desc'
    
    name = fields.Char(string='Tên đánh giá', required=True)
    employee_id = fields.Many2one('hr.employee', string='Nhân viên', required=True)
    assessor_id = fields.Many2one('hr.employee', string='Người đánh giá', required=True)
    assessment_date = fields.Date(string='Ngày đánh giá', required=True, default=fields.Date.today)
    
    # Assessment Type
    assessment_type = fields.Selection([
        ('self', 'Tự đánh giá'),
        ('supervisor', 'Đánh giá của cấp trên'),
        ('peer', 'Đánh giá đồng nghiệp'),
        ('360', 'Đánh giá 360 độ'),
        ('annual', 'Đánh giá thường niên'),
    ], string='Loại đánh giá', required=True, default='supervisor')
    
    # Status
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('submitted', 'Đã gửi'),
        ('reviewed', 'Đã duyệt'),
        ('approved', 'Đã phê duyệt'),
    ], string='Trạng thái', default='draft', tracking=True)
    
    # Assessment Lines
    skill_line_ids = fields.One2many('hdi.skill.assessment.line', 'assessment_id', string='Chi tiết đánh giá kỹ năng')
    competency_line_ids = fields.One2many('hdi.competency.assessment.line', 'assessment_id', string='Chi tiết đánh giá năng lực')
    
    # Scores
    total_skill_score = fields.Float(string='Tổng điểm kỹ năng', compute='_compute_total_scores')
    total_competency_score = fields.Float(string='Tổng điểm năng lực', compute='_compute_total_scores')
    overall_score = fields.Float(string='Điểm tổng', compute='_compute_total_scores')
    
    # Comments
    strengths = fields.Text(string='Điểm mạnh')
    areas_for_improvement = fields.Text(string='Điểm cần cải thiện')
    development_plan = fields.Text(string='Kế hoạch phát triển')
    assessor_comments = fields.Text(string='Nhận xét của người đánh giá')
    
    @api.depends('skill_line_ids.score', 'competency_line_ids.score')
    def _compute_total_scores(self):
        for assessment in self:
            skill_scores = assessment.skill_line_ids.mapped('score')
            competency_scores = assessment.competency_line_ids.mapped('score')
            
            assessment.total_skill_score = sum(skill_scores) / len(skill_scores) if skill_scores else 0
            assessment.total_competency_score = sum(competency_scores) / len(competency_scores) if competency_scores else 0
            assessment.overall_score = (assessment.total_skill_score + assessment.total_competency_score) / 2


class HdiSkillAssessmentLine(models.Model):
    """HDI Skill Assessment Lines"""
    _name = 'hdi.skill.assessment.line'
    _description = 'HDI Skill Assessment Line'
    
    assessment_id = fields.Many2one('hdi.skill.assessment', string='Đánh giá', required=True, ondelete='cascade')
    skill_id = fields.Many2one('hdi.skill', string='Kỹ năng', required=True)
    current_level = fields.Selection([
        ('beginner', 'Cơ bản'),
        ('intermediate', 'Trung bình'),
        ('advanced', 'Nâng cao'),
        ('expert', 'Chuyên gia'),
    ], string='Mức độ hiện tại', required=True)
    target_level = fields.Selection([
        ('beginner', 'Cơ bản'),
        ('intermediate', 'Trung bình'),
        ('advanced', 'Nâng cao'),
        ('expert', 'Chuyên gia'),
    ], string='Mức độ mục tiêu', required=True)
    score = fields.Float(string='Điểm số (1-5)', digits=(2, 1), required=True)
    evidence = fields.Text(string='Bằng chứng')
    development_action = fields.Text(string='Hành động phát triển')


class HdiCompetencyAssessmentLine(models.Model):
    """HDI Competency Assessment Lines"""
    _name = 'hdi.competency.assessment.line'
    _description = 'HDI Competency Assessment Line'
    
    assessment_id = fields.Many2one('hdi.skill.assessment', string='Đánh giá', required=True, ondelete='cascade')
    competency_id = fields.Many2one('hdi.competency', string='Năng lực', required=True)
    current_level = fields.Selection([
        ('1', 'Mức 1'),
        ('2', 'Mức 2'),
        ('3', 'Mức 3'),
        ('4', 'Mức 4'),
        ('5', 'Mức 5'),
    ], string='Mức độ hiện tại', required=True)
    target_level = fields.Selection([
        ('1', 'Mức 1'),
        ('2', 'Mức 2'),
        ('3', 'Mức 3'),
        ('4', 'Mức 4'),
        ('5', 'Mức 5'),
    ], string='Mức độ mục tiêu', required=True)
    score = fields.Float(string='Điểm số (1-5)', digits=(2, 1), required=True)
    evidence = fields.Text(string='Bằng chứng')
    development_action = fields.Text(string='Hành động phát triển')