# -*- coding: utf-8 -*-
from odoo import models, fields, api, _, exceptions
from odoo.exceptions import ValidationError


class NGSCInnovationScoringWizard(models.TransientModel):
  _name = 'ngsc.innovation.scoring.wizard'
  _description = 'Wizard chấm điểm ý tưởng sáng tạo - chỉ xử lý tiêu chí loại point'

  idea_id = fields.Many2one(
      'ngsc.innovation.idea',
      string='Ý tưởng',
      required=True,
      readonly=True
  )
  version_id = fields.Many2one(
      'ngsc.innovation.version',
      string='Phiên bản áp dụng',
      required=True,
      readonly=True
  )
  evaluator_id = fields.Many2one(
      'res.users',
      string='Người chấm',
      required=True,
      default=lambda self: self.env.user,
      readonly=True
  )
  total_score = fields.Float(
      string='Tổng điểm',
      compute='_compute_total_score',
      store=True,
      help='Chỉ tính tổng điểm cho các tiêu chí loại point'
  )
  scoring_line_ids = fields.One2many(
      'ngsc.innovation.scoring.wizard.line',
      'wizard_id',
      string='Chi tiết chấm điểm - chỉ tiêu chí loại point'
  )

  def _get_max_point_from_input(self, criteria):
    if not criteria.max_point_input:
      return 0.0

    try:
      input_value = str(criteria.max_point_input).strip()
      if not input_value:
        return 0.0
      result = float(input_value)
      return result if result > 0 else 0.0
    except (ValueError, TypeError):
      return 0.0

  @api.depends('scoring_line_ids.score_point')
  def _compute_total_score(self):
    for rec in self:
      total = sum(line.score_point for line in rec.scoring_line_ids if
                  line.criteria_type == 'point')
      rec.total_score = total

  @api.model
  def default_get(self, fields):
    res = super(NGSCInnovationScoringWizard, self).default_get(fields)
    active_id = self.env.context.get('active_id')

    if active_id:
      if not self.env[
        'ngsc.innovation.evaluation.period'].is_evaluation_period():
        raise ValidationError("Hiện không trong thời gian chấm điểm!")

      idea = self.env['ngsc.innovation.idea'].browse(active_id)
      version = self.env['ngsc.innovation.version'].search([
        ('status', '=', True)
      ], limit=1, order='start_date desc')

      if not version:
        raise ValidationError("Không tìm thấy phiên bản áp dụng!")

      criteria_list = self.env['ngsc.scoring.criteria'].search([
        ('version_id', '=', version.id),
        ('type', '=', 'point')
      ])

      scoring_lines = []
      for criteria in criteria_list:
        existing_score = self.env['ngsc.innovation.summary'].search([
          ('idea_id', '=', idea.id),
          ('criteria_id', '=', criteria.id),
          ('evaluator_id', '=', self.env.user.id),
          ('version_id', '=', version.id),
          ('is_latest', '=', True)
        ], limit=1)

        current_score = existing_score.score if existing_score else 0.0
        max_score_from_input = self._get_max_point_from_input(criteria)

        scoring_line_vals = {
          'criteria_id': criteria.id,
          'criteria_name': criteria.name,
          'criteria_type': criteria.type,
          'max_score_point': max_score_from_input,
          'score_point': current_score,
        }
        scoring_lines.append((0, 0, scoring_line_vals))

      res.update({
        'idea_id': idea.id,
        'version_id': version.id,
        'scoring_line_ids': scoring_lines
      })
    return res

  def action_submit_scores(self):
    self.ensure_one()

    if not self.env['ngsc.innovation.evaluation.period'].is_evaluation_period():
      raise ValidationError("Hiện không trong thời gian chấm điểm!")

    SummaryModel = self.env['ngsc.innovation.summary'].sudo()
    ScoringModel = self.env['ngsc.innovation.scoring'].sudo()

    try:
      with self.env.cr.savepoint():
        for line in self.scoring_line_ids:
          if not line.criteria_id:
            continue

          if line.criteria_type != 'point':
            continue

          score_value = line.score_point
          max_score = self._get_max_point_from_input(line.criteria_id)

          if score_value < 0:
            raise ValidationError(
                f"Điểm cho tiêu chí '{line.criteria_name}' không được âm")

          if max_score <= 0:
            raise ValidationError(
                f"Tiêu chí '{line.criteria_name}' chưa cấu hình điểm tối đa")

          if score_value > max_score:
            raise ValidationError(
                f"Điểm cho tiêu chí '{line.criteria_name}' không được vượt quá {max_score}")

          domain = [
            ('idea_id', '=', self.idea_id.id),
            ('criteria_id', '=', line.criteria_id.id),
            ('evaluator_id', '=', self.evaluator_id.id),
            ('version_id', '=', self.version_id.id),
            ('is_latest', '=', True)
          ]

          existing_score = SummaryModel.search(domain, limit=1)

          if existing_score:
            if existing_score.status:
              raise ValidationError(
                  f"Điểm cho tiêu chí '{line.criteria_name}' đã được chốt, không thể chỉnh sửa.")
            existing_score.write({'score': score_value})
          else:
            vals = {
              'idea_id': self.idea_id.id,
              'version_id': self.version_id.id,
              'criteria_id': line.criteria_id.id,
              'score': score_value,
              'evaluator_id': self.evaluator_id.id,
              'is_latest': True,
            }
            SummaryModel.create(vals)

          self._update_scoring_summary(line.criteria_id.id, ScoringModel)

        self.idea_id._compute_has_locked_scores()
        self.idea_id._compute_latest_scoring_ids()
        self.idea_id.invalidate_cache()

      self.env.cr.commit()

      return {
        'type': 'ir.actions.client',
        'tag': 'display_notification',
        'params': {
          'title': ('Thành công'),
          'message': ('Đã lưu điểm chấm thành công!'),
          'type': 'success',
          'sticky': False,
          'next': {
            'type': 'ir.actions.client',
            'tag': 'reload',
          }
        }
      }

    except Exception as e:
      raise ValidationError(f"Lỗi khi lưu điểm: {str(e)}")

  def _update_scoring_summary(self, criteria_id, ScoringModel):
    criteria = self.env['ngsc.scoring.criteria'].browse(criteria_id)
    if criteria.type != 'point':
      return False

    locked_summaries = self.env['ngsc.innovation.summary'].search([
      ('idea_id', '=', self.idea_id.id),
      ('version_id', '=', self.version_id.id),
      ('criteria_id', '=', criteria_id),
      ('is_latest', '=', True),
      ('status', '=', True)
    ])

    if not locked_summaries:
      return False

    scoring = ScoringModel.search([
      ('idea_id', '=', self.idea_id.id),
      ('version_id', '=', self.version_id.id),
      ('criteria_id', '=', criteria_id)
    ], limit=1)

    if scoring:
      total_score = sum(locked_summaries.mapped('score'))
      number_of_evaluators = len(locked_summaries)
      average_score = total_score / number_of_evaluators if number_of_evaluators > 0 else 0

      scoring.write({
        'total_score': total_score,
        'number_of_evaluators': number_of_evaluators,
        'average_score': average_score,
      })
    else:
      ScoringModel.create({
        'idea_id': self.idea_id.id,
        'version_id': self.version_id.id,
        'criteria_id': criteria_id,
        'total_score': sum(locked_summaries.mapped('score')),
        'number_of_evaluators': len(locked_summaries),
        'average_score': (
          sum(locked_summaries.mapped('score')) / len(locked_summaries)
          if locked_summaries else 0
        ),
      })


class NGSCInnovationScoringWizardLine(models.TransientModel):
  _name = 'ngsc.innovation.scoring.wizard.line'
  _description = 'Chi tiết chấm điểm trong wizard - chỉ cho tiêu chí loại point'

  wizard_id = fields.Many2one(
      'ngsc.innovation.scoring.wizard',
      string='Wizard'
  )
  criteria_id = fields.Many2one(
      'ngsc.scoring.criteria',
      string='Tiêu chí',
      required=True,
      domain=[('type', '=', 'point')]
  )
  criteria_name = fields.Char(
      string='Tên tiêu chí'
  )
  criteria_type = fields.Selection([
    ('point', 'Điểm'),
  ], string='Kiểu chấm điểm', default='point', readonly=True)

  max_score_point = fields.Float(
      string='Điểm tối đa',
      help='Điểm tối đa cho tiêu chí loại point (lấy từ max_point_input)'
  )

  score_point = fields.Float(
      string='Điểm',
      help='Điểm chấm cho tiêu chí',
      required=True
  )

  @api.constrains('criteria_id')
  def _check_criteria_type(self):
    for rec in self:
      if rec.criteria_id.type != 'point':
        raise ValidationError(
            "Chỉ được phép chấm điểm cho tiêu chí loại 'Điểm'")