# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta


class HdiPerformanceEvaluation(models.Model):
  """HDI Performance Evaluation System"""
  _name = 'hdi.performance.evaluation'
  _description = 'HDI Performance Evaluation'
  _inherit = ['mail.thread', 'mail.activity.mixin']
  _order = 'evaluation_date desc, id desc'
  _rec_name = 'display_name'

  # Basic Information
  name = fields.Char(string='Tên đánh giá', required=True, tracking=True)
  display_name = fields.Char(string='Tên hiển thị',
                             compute='_compute_display_name', store=True)
  employee_id = fields.Many2one('hr.employee', string='Nhân viên',
                                required=True, tracking=True)
  evaluator_id = fields.Many2one('hr.employee', string='Người đánh giá',
                                 required=True, tracking=True)
  evaluation_date = fields.Date(string='Ngày đánh giá', required=True,
                                default=fields.Date.today, tracking=True)

  # Evaluation Period
  period_from = fields.Date(string='Từ ngày', required=True, tracking=True)
  period_to = fields.Date(string='Đến ngày', required=True, tracking=True)

  # Evaluation Type & Template
  evaluation_type = fields.Selection([
    ('probation', 'Đánh giá thử việc'),
    ('quarterly', 'Đánh giá quý'),
    ('semi_annual', 'Đánh giá 6 tháng'),
    ('annual', 'Đánh giá thường niên'),
    ('project_based', 'Đánh giá theo dự án'),
    ('promotion', 'Đánh giá thăng chức'),
    ('ad_hoc', 'Đánh giá đột xuất'),
  ], string='Loại đánh giá', required=True, default='quarterly', tracking=True)

  evaluation_template_id = fields.Many2one(
      'hdi.performance.template',
      string='Mẫu đánh giá',
      tracking=True
  )

  # Status & Workflow
  state = fields.Selection([
    ('draft', 'Nháp'),
    ('employee_review', 'Nhân viên tự đánh giá'),
    ('manager_review', 'Quản lý đánh giá'),
    ('hr_review', 'HR xem xét'),
    ('approved', 'Đã phê duyệt'),
    ('cancelled', 'Đã hủy'),
  ], string='Trạng thái', default='draft', tracking=True)

  # Scores & Results
  self_total_score = fields.Float(string='Điểm tự đánh giá',
                                  compute='_compute_scores', store=True)
  manager_total_score = fields.Float(string='Điểm người quản lý',
                                     compute='_compute_scores', store=True)
  final_score = fields.Float(string='Điểm cuối cùng', compute='_compute_scores',
                             store=True, tracking=True)

  performance_rating = fields.Selection([
    ('poor', 'Kém (1-2)'),
    ('below_average', 'Dưới trung bình (2-3)'),
    ('average', 'Trung bình (3-3.5)'),
    ('good', 'Tốt (3.5-4)'),
    ('excellent', 'Xuất sắc (4-5)'),
  ], string='Xếp loại', compute='_compute_performance_rating', store=True,
      tracking=True)

  # Goal Achievement
  goal_achievement_rate = fields.Float(string='Tỷ lệ đạt mục tiêu (%)',
                                       tracking=True)

  # Comments & Feedback
  employee_comments = fields.Text(string='Nhận xét của nhân viên')
  manager_comments = fields.Text(string='Nhận xét của quản lý')
  hr_comments = fields.Text(string='Nhận xét của HR')

  strengths = fields.Text(string='Điểm mạnh')
  areas_for_improvement = fields.Text(string='Điểm cần cải thiện')
  development_plan = fields.Text(string='Kế hoạch phát triển')
  career_aspirations = fields.Text(string='Định hướng phát triển sự nghiệp')

  # Recommendations
  salary_recommendation = fields.Selection([
    ('no_change', 'Không thay đổi'),
    ('increase', 'Tăng lương'),
    ('decrease', 'Giảm lương'),
    ('bonus', 'Thưởng'),
  ], string='Đề xuất lương')

  promotion_recommendation = fields.Selection([
    ('no_change', 'Không thay đổi'),
    ('promote', 'Thăng chức'),
    ('lateral_move', 'Chuyển vị trí ngang cấp'),
    ('demotion', 'Giáng chức'),
  ], string='Đề xuất thăng tiến')

  training_recommendation = fields.Text(string='Đề xuất đào tạo')

  # Related Records
  kpi_line_ids = fields.One2many(
      'hdi.performance.kpi.line',
      'evaluation_id',
      string='KPI đánh giá'
  )

  competency_line_ids = fields.One2many(
      'hdi.performance.competency.line',
      'evaluation_id',
      string='Đánh giá năng lực'
  )

  goal_line_ids = fields.One2many(
      'hdi.performance.goal.line',
      'evaluation_id',
      string='Mục tiêu cá nhân'
  )

  # Dates
  employee_deadline = fields.Date(string='Hạn nhân viên tự đánh giá')
  manager_deadline = fields.Date(string='Hạn quản lý đánh giá')

  # Computed Fields
  is_overdue = fields.Boolean(string='Quá hạn', compute='_compute_overdue',
                              store=True)

  @api.depends('employee_id', 'evaluation_type', 'evaluation_date')
  def _compute_display_name(self):
    for evaluation in self:
      if evaluation.employee_id:
        evaluation.display_name = f"{evaluation.employee_id.name} - {dict(evaluation._fields['evaluation_type'].selection).get(evaluation.evaluation_type, '')} - {evaluation.evaluation_date}"
      else:
        evaluation.display_name = evaluation.name or 'Đánh giá hiệu suất'

  @api.depends('kpi_line_ids.self_score', 'kpi_line_ids.manager_score',
               'kpi_line_ids.final_score')
  def _compute_scores(self):
    for evaluation in self:
      kpi_lines = evaluation.kpi_line_ids.filtered(lambda l: l.weight > 0)

      if kpi_lines:
        # Tính điểm tự đánh giá
        self_scores = [(line.self_score * line.weight / 100) for line in
                       kpi_lines if line.self_score]
        evaluation.self_total_score = sum(self_scores) if self_scores else 0.0

        # Tính điểm quản lý đánh giá
        manager_scores = [(line.manager_score * line.weight / 100) for line in
                          kpi_lines if line.manager_score]
        evaluation.manager_total_score = sum(
          manager_scores) if manager_scores else 0.0

        # Tính điểm cuối cùng
        final_scores = [(line.final_score * line.weight / 100) for line in
                        kpi_lines if line.final_score]
        evaluation.final_score = sum(final_scores) if final_scores else 0.0
      else:
        evaluation.self_total_score = 0.0
        evaluation.manager_total_score = 0.0
        evaluation.final_score = 0.0

  @api.depends('final_score')
  def _compute_performance_rating(self):
    for evaluation in self:
      if evaluation.final_score >= 4.0:
        evaluation.performance_rating = 'excellent'
      elif evaluation.final_score >= 3.5:
        evaluation.performance_rating = 'good'
      elif evaluation.final_score >= 3.0:
        evaluation.performance_rating = 'average'
      elif evaluation.final_score >= 2.0:
        evaluation.performance_rating = 'below_average'
      else:
        evaluation.performance_rating = 'poor'

  @api.depends('employee_deadline', 'manager_deadline', 'state')
  def _compute_overdue(self):
    today = fields.Date.today()
    for evaluation in self:
      is_overdue = False
      if evaluation.state == 'employee_review' and evaluation.employee_deadline and evaluation.employee_deadline < today:
        is_overdue = True
      elif evaluation.state == 'manager_review' and evaluation.manager_deadline and evaluation.manager_deadline < today:
        is_overdue = True
      evaluation.is_overdue = is_overdue

  @api.model
  def create(self, vals):
    """Tự động thiết lập deadline khi tạo đánh giá"""
    evaluation = super().create(vals)

    # Tự động set deadline nếu chưa có
    if not evaluation.employee_deadline:
      evaluation.employee_deadline = fields.Date.today() + timedelta(days=7)
    if not evaluation.manager_deadline:
      evaluation.manager_deadline = fields.Date.today() + timedelta(days=14)

    return evaluation

  def action_start_employee_review(self):
    """Bắt đầu nhân viên tự đánh giá"""
    for evaluation in self:
      if evaluation.state != 'draft':
        raise UserError(_('Chỉ có thể bắt đầu đánh giá từ trạng thái nháp!'))

      evaluation.write({'state': 'employee_review'})

      # Gửi thông báo cho nhân viên
      if evaluation.employee_id.user_id:
        evaluation.activity_schedule(
            'mail.mail_activity_data_todo',
            user_id=evaluation.employee_id.user_id.id,
            summary=f'Tự đánh giá hiệu suất - {evaluation.name}',
            note=f'Bạn có đánh giá hiệu suất cần hoàn thành trước {evaluation.employee_deadline}',
            date_deadline=evaluation.employee_deadline,
        )

  def action_submit_employee_review(self):
    """Nhân viên submit tự đánh giá"""
    for evaluation in self:
      if evaluation.state != 'employee_review':
        raise UserError(_('Không thể submit ở trạng thái hiện tại!'))

      evaluation.write({'state': 'manager_review'})

      # Gửi thông báo cho quản lý
      if evaluation.evaluator_id.user_id:
        evaluation.activity_schedule(
            'mail.mail_activity_data_todo',
            user_id=evaluation.evaluator_id.user_id.id,
            summary=f'Đánh giá hiệu suất nhân viên - {evaluation.employee_id.name}',
            note=f'Nhân viên {evaluation.employee_id.name} đã hoàn thành tự đánh giá. Vui lòng hoàn thành đánh giá trước {evaluation.manager_deadline}',
            date_deadline=evaluation.manager_deadline,
        )

  def action_submit_manager_review(self):
    """Quản lý submit đánh giá"""
    for evaluation in self:
      if evaluation.state != 'manager_review':
        raise UserError(_('Không thể submit ở trạng thái hiện tại!'))

      evaluation.write({'state': 'hr_review'})

      # Gửi thông báo cho HR
      hr_users = self.env.ref('hr.group_hr_user').users
      if hr_users:
        for user in hr_users:
          evaluation.activity_schedule(
              'mail.mail_activity_data_todo',
              user_id=user.id,
              summary=f'Xem xét đánh giá hiệu suất - {evaluation.employee_id.name}',
              note=f'Đánh giá hiệu suất của {evaluation.employee_id.name} cần được xem xét và phê duyệt',
          )

  def action_approve(self):
    """HR phê duyệt đánh giá"""
    for evaluation in self:
      if evaluation.state != 'hr_review':
        raise UserError(_('Không thể phê duyệt ở trạng thái hiện tại!'))

      evaluation.write({'state': 'approved'})

      # Cập nhật thông tin hiệu suất cho nhân viên
      evaluation.employee_id.write({
        'hdi_performance_level': evaluation.performance_rating,
        'hdi_average_performance_score': evaluation.final_score,
      })

  def action_cancel(self):
    """Hủy đánh giá"""
    for evaluation in self:
      evaluation.write({'state': 'cancelled'})

  def action_reset_to_draft(self):
    """Reset về nháp"""
    for evaluation in self:
      evaluation.write({'state': 'draft'})


class HdiPerformanceTemplate(models.Model):
  """Performance Evaluation Templates"""
  _name = 'hdi.performance.template'
  _description = 'HDI Performance Template'
  _order = 'name'

  name = fields.Char(string='Tên mẫu đánh giá', required=True)
  description = fields.Text(string='Mô tả')
  evaluation_type = fields.Selection([
    ('probation', 'Đánh giá thử việc'),
    ('quarterly', 'Đánh giá quý'),
    ('semi_annual', 'Đánh giá 6 tháng'),
    ('annual', 'Đánh giá thường niên'),
    ('project_based', 'Đánh giá theo dự án'),
    ('promotion', 'Đánh giá thăng chức'),
  ], string='Loại đánh giá', required=True)

  active = fields.Boolean(string='Kích hoạt', default=True)

  # Template Lines
  kpi_template_ids = fields.One2many(
      'hdi.performance.kpi.template',
      'template_id',
      string='KPI mẫu'
  )

  competency_template_ids = fields.One2many(
      'hdi.performance.competency.template',
      'template_id',
      string='Năng lực mẫu'
  )


class HdiPerformanceKpiLine(models.Model):
  """Performance KPI Lines"""
  _name = 'hdi.performance.kpi.line'
  _description = 'HDI Performance KPI Line'
  _order = 'sequence, id'

  evaluation_id = fields.Many2one('hdi.performance.evaluation',
                                  string='Đánh giá', required=True,
                                  ondelete='cascade')
  sequence = fields.Integer(string='Thứ tự', default=10)

  name = fields.Char(string='Tên KPI', required=True)
  description = fields.Text(string='Mô tả')
  measurement = fields.Char(string='Cách đo lường')
  target = fields.Char(string='Mục tiêu')
  weight = fields.Float(string='Trọng số (%)', required=True, default=0.0)

  # Scores
  self_score = fields.Float(string='Điểm tự đánh giá (1-5)', digits=(3, 1))
  self_comment = fields.Text(string='Nhận xét tự đánh giá')

  manager_score = fields.Float(string='Điểm quản lý (1-5)', digits=(3, 1))
  manager_comment = fields.Text(string='Nhận xét quản lý')

  final_score = fields.Float(string='Điểm cuối cùng (1-5)', digits=(3, 1))

  achievement_evidence = fields.Text(string='Bằng chứng thực hiện')


class HdiPerformanceCompetencyLine(models.Model):
  """Performance Competency Lines"""
  _name = 'hdi.performance.competency.line'
  _description = 'HDI Performance Competency Line'

  evaluation_id = fields.Many2one('hdi.performance.evaluation',
                                  string='Đánh giá', required=True,
                                  ondelete='cascade')
  competency_id = fields.Many2one('hdi.competency', string='Năng lực',
                                  required=True)

  # Scores
  self_score = fields.Float(string='Điểm tự đánh giá (1-5)', digits=(3, 1))
  self_comment = fields.Text(string='Nhận xét tự đánh giá')

  manager_score = fields.Float(string='Điểm quản lý (1-5)', digits=(3, 1))
  manager_comment = fields.Text(string='Nhận xét quản lý')

  final_score = fields.Float(string='Điểm cuối cùng (1-5)', digits=(3, 1))


class HdiPerformanceGoalLine(models.Model):
  """Performance Goal Lines"""
  _name = 'hdi.performance.goal.line'
  _description = 'HDI Performance Goal Line'

  evaluation_id = fields.Many2one('hdi.performance.evaluation',
                                  string='Đánh giá', required=True,
                                  ondelete='cascade')

  name = fields.Char(string='Mục tiêu', required=True)
  description = fields.Text(string='Mô tả chi tiết')
  target_date = fields.Date(string='Ngày hoàn thành mục tiêu')

  achievement_rate = fields.Float(string='Tỷ lệ hoàn thành (%)', default=0.0)
  achievement_comment = fields.Text(string='Nhận xét về việc hoàn thành')

  status = fields.Selection([
    ('not_started', 'Chưa bắt đầu'),
    ('in_progress', 'Đang thực hiện'),
    ('completed', 'Hoàn thành'),
    ('overdue', 'Quá hạn'),
    ('cancelled', 'Hủy bỏ'),
  ], string='Trạng thái', default='not_started')


# Template Models
class HdiPerformanceKpiTemplate(models.Model):
  _name = 'hdi.performance.kpi.template'
  _description = 'HDI Performance KPI Template'

  template_id = fields.Many2one('hdi.performance.template', string='Mẫu',
                                required=True, ondelete='cascade')
  sequence = fields.Integer(string='Thứ tự', default=10)
  name = fields.Char(string='Tên KPI', required=True)
  description = fields.Text(string='Mô tả')
  measurement = fields.Char(string='Cách đo lường')
  target = fields.Char(string='Mục tiêu')
  weight = fields.Float(string='Trọng số (%)', required=True, default=0.0)


class HdiPerformanceCompetencyTemplate(models.Model):
  _name = 'hdi.performance.competency.template'
  _description = 'HDI Performance Competency Template'

  template_id = fields.Many2one('hdi.performance.template', string='Mẫu',
                                required=True, ondelete='cascade')
  competency_id = fields.Many2one('hdi.competency', string='Năng lực',
                                  required=True)