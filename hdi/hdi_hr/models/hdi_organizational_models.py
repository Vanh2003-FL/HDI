# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class HdiBlock(models.Model):
    """HDI Organizational Block - Khối"""
    _name = 'hdi.block'
    _description = 'HDI Organizational Block'
    _order = 'sequence, name'
    
    name = fields.Char(string='Tên khối', required=True)
    code = fields.Char(string='Mã khối', required=True)
    sequence = fields.Integer(string='Thứ tự', default=10)
    description = fields.Text(string='Mô tả')
    manager_id = fields.Many2one('hr.employee', string='Người phụ trách')
    department_ids = fields.One2many('hr.department', 'hdi_block_id', string='Phòng ban')
    employee_count = fields.Integer(string='Số nhân viên', compute='_compute_employee_count')
    active = fields.Boolean(string='Kích hoạt', default=True)
    
    @api.depends('department_ids.member_ids')
    def _compute_employee_count(self):
        for block in self:
            block.employee_count = len(block.department_ids.mapped('member_ids'))


class HdiArea(models.Model):
    """HDI Area - Khu vực"""
    _name = 'hdi.area'
    _description = 'HDI Area'
    _order = 'sequence, name'
    
    name = fields.Char(string='Tên khu vực', required=True)
    code = fields.Char(string='Mã khu vực', required=True)
    sequence = fields.Integer(string='Thứ tự', default=10)
    description = fields.Text(string='Mô tả')
    employee_ids = fields.One2many('hr.employee', 'hdi_area_id', string='Nhân viên')
    employee_count = fields.Integer(string='Số nhân viên', compute='_compute_employee_count')
    active = fields.Boolean(string='Kích hoạt', default=True)
    
    @api.depends('employee_ids')
    def _compute_employee_count(self):
        for area in self:
            area.employee_count = len(area.employee_ids)


class HdiLevel(models.Model):
    """HDI Level - Cấp bậc"""
    _name = 'hdi.level'
    _description = 'HDI Level'
    _order = 'sequence, name'
    
    name = fields.Char(string='Tên cấp bậc', required=True)
    code = fields.Char(string='Mã cấp bậc', required=True)
    sequence = fields.Integer(string='Thứ tự', default=10)
    level_type = fields.Selection([
        ('staff', 'Nhân viên'),
        ('supervisor', 'Giám sát'),
        ('manager', 'Quản lý'),
        ('senior_manager', 'Quản lý cao cấp'),
        ('director', 'Giám đốc'),
        ('executive', 'Điều hành'),
    ], string='Loại cấp bậc', required=True)
    salary_min = fields.Monetary(string='Lương tối thiểu', currency_field='currency_id')
    salary_max = fields.Monetary(string='Lương tối đa', currency_field='currency_id')
    description = fields.Text(string='Mô tả')
    employee_ids = fields.One2many('hr.employee', 'hdi_level_id', string='Nhân viên')
    employee_count = fields.Integer(string='Số nhân viên', compute='_compute_employee_count')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    active = fields.Boolean(string='Kích hoạt', default=True)
    
    @api.depends('employee_ids')
    def _compute_employee_count(self):
        for level in self:
            level.employee_count = len(level.employee_ids)


class HdiUnit(models.Model):
    """HDI Unit - Đơn vị"""
    _name = 'hdi.unit'
    _description = 'HDI Unit'
    _order = 'sequence, name'
    _parent_store = True
    
    name = fields.Char(string='Tên đơn vị', required=True)
    code = fields.Char(string='Mã đơn vị', required=True)
    sequence = fields.Integer(string='Thứ tự', default=10)
    parent_id = fields.Many2one('hdi.unit', string='Đơn vị cha')
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many('hdi.unit', 'parent_id', string='Đơn vị con')
    department_id = fields.Many2one('hr.department', string='Thuộc phòng ban')
    manager_id = fields.Many2one('hr.employee', string='Người phụ trách')
    employee_ids = fields.One2many('hr.employee', 'hdi_unit_id', string='Nhân viên')
    employee_count = fields.Integer(string='Số nhân viên', compute='_compute_employee_count')
    description = fields.Text(string='Mô tả')
    active = fields.Boolean(string='Kích hoạt', default=True)
    
    @api.depends('employee_ids')
    def _compute_employee_count(self):
        for unit in self:
            unit.employee_count = len(unit.employee_ids)


class HdiEmployeeCompetency(models.Model):
    """HDI Employee Competencies"""
    _name = 'hdi.employee.competency'
    _description = 'HDI Employee Competencies'
    _rec_name = 'competency_id'
    
    employee_id = fields.Many2one('hr.employee', string='Nhân viên', required=True, ondelete='cascade')
    competency_id = fields.Many2one('hdi.competency', string='Năng lực', required=True)
    level = fields.Selection([
        ('1', 'Mức 1 - Cơ bản'),
        ('2', 'Mức 2 - Phát triển'),
        ('3', 'Mức 3 - Thành thạo'),
        ('4', 'Mức 4 - Nâng cao'),
        ('5', 'Mức 5 - Chuyên gia'),
    ], string='Mức độ', required=True, default='1')
    current_score = fields.Float(string='Điểm hiện tại', digits=(3, 2))
    target_score = fields.Float(string='Điểm mục tiêu', digits=(3, 2))
    assessment_date = fields.Date(string='Ngày đánh giá')
    assessor_id = fields.Many2one('hr.employee', string='Người đánh giá')
    development_plan = fields.Text(string='Kế hoạch phát triển')
    
    _sql_constraints = [
        ('unique_employee_competency', 'unique(employee_id, competency_id)', 
         'Một nhân viên không thể có cùng một năng lực hai lần!'),
    ]


class HdiEmployeeLanguage(models.Model):
    """HDI Employee Languages"""
    _name = 'hdi.employee.language'
    _description = 'HDI Employee Languages'
    
    employee_id = fields.Many2one('hr.employee', string='Nhân viên', required=True, ondelete='cascade')
    language = fields.Selection([
        ('english', 'Tiếng Anh'),
        ('japanese', 'Tiếng Nhật'),
        ('korean', 'Tiếng Hàn'),
        ('chinese', 'Tiếng Trung'),
        ('french', 'Tiếng Pháp'),
        ('german', 'Tiếng Đức'),
        ('other', 'Khác'),
    ], string='Ngoại ngữ', required=True)
    other_language = fields.Char(string='Ngoại ngữ khác', help='Điền nếu chọn "Khác"')
    level = fields.Selection([
        ('basic', 'Cơ bản'),
        ('intermediate', 'Trung bình'),
        ('advanced', 'Nâng cao'),
        ('fluent', 'Thông thạo'),
        ('native', 'Bản ngữ'),
    ], string='Trình độ', required=True, default='basic')
    listening = fields.Selection([
        ('poor', 'Kém'),
        ('fair', 'Trung bình'),
        ('good', 'Tốt'),
        ('excellent', 'Xuất sắc'),
    ], string='Nghe')
    speaking = fields.Selection([
        ('poor', 'Kém'),
        ('fair', 'Trung bình'),
        ('good', 'Tốt'),
        ('excellent', 'Xuất sắc'),
    ], string='Nói')
    reading = fields.Selection([
        ('poor', 'Kém'),
        ('fair', 'Trung bình'),
        ('good', 'Tốt'),
        ('excellent', 'Xuất sắc'),
    ], string='Đọc')
    writing = fields.Selection([
        ('poor', 'Kém'),
        ('fair', 'Trung bình'),
        ('good', 'Tốt'),
        ('excellent', 'Xuất sắc'),
    ], string='Viết')
    certificate = fields.Char(string='Chứng chỉ')
    certificate_score = fields.Char(string='Điểm số')
    certificate_date = fields.Date(string='Ngày cấp')
    
    _sql_constraints = [
        ('unique_employee_language', 'unique(employee_id, language)', 
         'Một nhân viên không thể có cùng một ngoại ngữ hai lần!'),
    ]