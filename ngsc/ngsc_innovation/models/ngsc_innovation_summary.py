from odoo import models, fields, api, _, exceptions
from odoo.exceptions import UserError, ValidationError


class NGSCInnovationSummary(models.Model):
  _name = 'ngsc.innovation.summary'
  _description = 'Tổng hợp chấm điểm ý tưởng sáng tạo'

  idea_id = fields.Many2one(
      'ngsc.innovation.idea',
      string='Ý tưởng',
      required=True,
      ondelete='cascade'
  )
  version_id = fields.Many2one(
      'ngsc.innovation.version',
      string='Phiên bản áp dụng',
      required=True
  )
  criteria_id = fields.Many2one(
      'ngsc.scoring.criteria',
      string='Tiêu chí',
      required=True,
      domain=[('type', '=', 'point')]
  )
  type_criteria = fields.Selection(
      selection=[
        ('percent', 'Phần trăm (%)'),
        ('point', 'Điểm'),
        ('grade', 'Xếp hạng (A, B, C, D, F)'),
        ('boolean', 'Pass / Fail (T/F)'),
      ],
      string='Kiểu chấm điểm',
      related='criteria_id.type',
      readonly=True,
  )
  score = fields.Float(
      string='Số điểm',
      help='Chỉ lưu điểm cho tiêu chí loại point'
  )
  evaluator_id = fields.Many2one(
      'res.users',
      string='Người chấm',
      required=True,
      default=lambda self: self.env.user
  )
  status = fields.Boolean(
      string='Đã chốt điểm',
      default=False,
      help='Nếu tick, điểm không được phép chỉnh sửa'
  )

  history_ids = fields.One2many(
      'ngsc.innovation.summary',
      'parent_id',
      string='Lịch sử sửa điểm'
  )
  parent_id = fields.Many2one(
      'ngsc.innovation.summary',
      string='Bản ghi gốc'
  )
  is_latest = fields.Boolean(
      string='Bản ghi mới nhất',
      default=True,
      help='Đánh dấu bản ghi chấm điểm mới nhất để tính toán tổng hợp'
  )

  idea_name = fields.Char(string='Tên ý tưởng', related='idea_id.idea_name',
                          readonly=True)

  idea_state = fields.Selection(
      string='Trạng thái ý tưởng',
      related='idea_id.state',
      readonly=True,
  )

  _sql_constraints = [
    ('unique_idea_criteria_evaluator',
     'unique(idea_id, criteria_id, evaluator_id, version_id) WHERE is_latest = true',
     'Mỗi tiêu chí chỉ được tính một lần cho mỗi ý tưởng bởi cùng một người chấm!')
  ]

  def _get_max_score_from_criteria(self, criteria):
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

  @api.constrains('score', 'criteria_id')
  def _check_score_limit(self):
    for rec in self:
      criteria = rec.criteria_id
      if not criteria or rec.score is False:
        continue

      if criteria.type != 'point':
        raise ValidationError(
            f"Chỉ được phép lưu điểm cho tiêu chí loại 'Điểm'")

      max_score = rec._get_max_score_from_criteria(criteria)

      if max_score <= 0:
        raise ValidationError(
            f"Tiêu chí '{criteria.name}' chưa được cấu hình điểm tối đa hợp lệ. "
            f"Giá trị hiện tại trong max_point_input: '{criteria.max_point_input}'")

      if rec.score < 0 or rec.score > max_score:
        raise ValidationError(
            f"Giá trị điểm cho tiêu chí '{criteria.name}' phải từ 0 đến {max_score}")

  @api.model
  def create(self, vals):
    if 'criteria_id' in vals:
      criteria = self.env['ngsc.scoring.criteria'].browse(vals['criteria_id'])
      if criteria.type != 'point':
        raise ValidationError(
            "Chỉ được phép tạo bản ghi cho tiêu chí loại 'Điểm'")

    # Check if user is TTNB or evaluation board member
    is_ttnb = self.env.user.has_group(
        'ngsc_innovation.group_internal_communication')
    is_evaluator = self.env.user.has_group(
        'ngsc_innovation.group_evaluation_board')

    if not (is_ttnb or is_evaluator):
      raise UserError('Bạn không có quyền chấm điểm.')

    idea = self.env['ngsc.innovation.idea'].browse(vals.get('idea_id'))
    if idea.state != 'approved':
      raise UserError('Chỉ được chấm điểm cho ý tưởng đã duyệt.')

    current_user_id = vals.get('evaluator_id', self.env.user.id)
    existing_locked = self.search([
      ('idea_id', '=', vals.get('idea_id')),
      ('evaluator_id', '=', current_user_id),
      ('is_latest', '=', True),
      ('status', '=', True)
    ])
    if existing_locked and not is_ttnb:
      raise UserError('Bạn đã chốt điểm, không thể tạo điểm mới.')

    if vals.get('is_latest', True) and not vals.get('parent_id'):
      existing_records = self.search([
        ('idea_id', '=', vals.get('idea_id')),
        ('criteria_id', '=', vals.get('criteria_id')),
        ('evaluator_id', '=', vals.get('evaluator_id')),
        ('version_id', '=', vals.get('version_id')),
        ('is_latest', '=', True)
      ])
      if existing_records:
        existing_records.write({'is_latest': False})

    result = super(NGSCInnovationSummary, self).create(vals)

    if result.is_latest and not result.parent_id and result.criteria_id.type == 'point':
      self.env['ngsc.innovation.scoring'].create_or_update_summary(
          result.idea_id.id, result.version_id.id, result.criteria_id.id
      )

    return result

  def write(self, vals):
    is_ttnb = self.env.user.has_group(
        'ngsc_innovation.group_internal_communication')
    is_evaluator = self.env.user.has_group(
        'ngsc_innovation.group_evaluation_board')

    for rec in self:
      if rec.status and any(
          key in vals for key in ['score', 'criteria_id']) and not is_ttnb:
        raise UserError("Điểm đã chốt, không thể chỉnh sửa.")

      if not (is_ttnb or is_evaluator):
        raise UserError('Bạn không có quyền chỉnh sửa điểm.')

      # TTNB can edit any score, evaluators can only edit their own
      if not is_ttnb and rec.evaluator_id.id != self.env.user.id:
        raise UserError('Bạn chỉ có thể sửa điểm của chính mình.')

      if 'criteria_id' in vals:
        criteria = self.env['ngsc.scoring.criteria'].browse(
            vals['criteria_id'])
        if criteria.type != 'point':
          raise ValidationError(
              "Chỉ được phép cập nhật cho tiêu chí loại 'Điểm'")

    if 'score' in vals:
      for rec in self:
        if rec.is_latest and rec.score != vals.get('score'):
          history_vals = {
            'idea_id': rec.idea_id.id,
            'version_id': rec.version_id.id,
            'criteria_id': rec.criteria_id.id,
            'score': rec.score,
            'evaluator_id': rec.evaluator_id.id,
            'parent_id': rec.id,
            'is_latest': False,
          }
          self.sudo().create(history_vals)

    result = super(NGSCInnovationSummary, self).write(vals)

    if 'score' in vals:
      for rec in self:
        if rec.is_latest and rec.criteria_id.type == 'point':
          scoring_model = self.env['ngsc.innovation.scoring']
          scoring_model.create_or_update_summary(
              rec.idea_id.id, rec.version_id.id, rec.criteria_id.id
          )

    return result

  def unlink(self):
    is_ttnb = self.env.user.has_group(
        'ngsc_innovation.group_internal_communication')
    is_evaluator = self.env.user.has_group(
        'ngsc_innovation.group_evaluation_board')

    for rec in self:
      if rec.status and not is_ttnb:
        raise UserError('Không thể xóa bản ghi điểm đã chốt.')

      if not is_ttnb and rec.evaluator_id.id != self.env.user.id:
        raise UserError('Bạn chỉ có thể xóa điểm của chính mình.')

      if not (is_ttnb or is_evaluator):
        raise UserError('Bạn không có quyền xóa điểm.')

    return super(NGSCInnovationSummary, self).unlink()

  def get_numeric_score(self):
    self.ensure_one()
    if self.type_criteria == 'point':
      return float(self.score or 0)
    return 0

class NGSCInnovationScoring(models.Model):
  _name = 'ngsc.innovation.scoring'
  _description = 'Tổng hợp điểm ý tưởng'
  _order = 'idea_id, criteria_id'

  idea_id = fields.Many2one(
      'ngsc.innovation.idea',
      string='Ý tưởng',
      required=True,
      ondelete='cascade'
  )

  version_id = fields.Many2one(
      'ngsc.innovation.version',
      string='Phiên bản áp dụng',
      required=True
  )

  criteria_id = fields.Many2one(
      'ngsc.scoring.criteria',
      string='Tiêu chí',
      required=True,
      domain=[('type', '=', 'point')]
  )

  detail_ids = fields.Many2many(
      'ngsc.innovation.summary',
      compute='_compute_detail_ids',
      string='Chi tiết điểm',
      help='Danh sách điểm mới nhất của từng người chấm cho tiêu chí loại point'
  )

  total_score = fields.Float(
      string='Số điểm',
      compute='_compute_scores',
      help='Tổng điểm của tất cả người chấm cho tiêu chí'
  )

  average_score = fields.Float(
      string='Điểm trung bình',
      compute='_compute_scores',
      store=True,
      help='Điểm trung bình của tiêu chí'
  )

  number_of_evaluators = fields.Integer(
      string='Số người chấm',
      compute='_compute_scores',
      store=True,
      help='Số người đã chấm điểm cho tiêu chí này (chỉ tính point)'
  )

  _sql_constraints = [
    ('unique_idea_criteria_version',
     'unique(idea_id, criteria_id, version_id)',
     'Mỗi tiêu chí chỉ có một bản tổng hợp cho mỗi ý tưởng trong cùng phiên bản!')
  ]

  @api.constrains('criteria_id')
  def _check_criteria_type(self):
    for rec in self:
      if rec.criteria_id.type != 'point':
        raise ValidationError(
            "Chỉ được phép tạo tổng hợp cho tiêu chí loại 'Điểm'")

  @api.depends('idea_id', 'criteria_id', 'version_id')
  def _compute_detail_ids(self):
    for record in self:
      if record.idea_id and record.criteria_id and record.criteria_id.type == 'point':
        details = self.env['ngsc.innovation.summary'].search([
          ('idea_id', '=', record.idea_id.id),
          ('criteria_id', '=', record.criteria_id.id),
          ('version_id', '=', record.version_id.id),
          ('is_latest', '=', True)
        ])
        record.detail_ids = details
      else:
        record.detail_ids = False

  @api.depends('detail_ids.score', 'detail_ids.status')
  def _compute_scores(self):
    for record in self:
      if record.criteria_id.type != 'point':
        record.total_score = 0.0
        record.average_score = 0.0
        record.number_of_evaluators = 0
        continue

      locked_details = self.env['ngsc.innovation.summary'].search([
        ('idea_id', '=', record.idea_id.id),
        ('criteria_id', '=', record.criteria_id.id),
        ('version_id', '=', record.version_id.id),
        ('is_latest', '=', True),
        ('status', '=', True)
      ])

      if locked_details:
        numeric_scores = [detail.get_numeric_score() for detail in
                          locked_details]
        record.total_score = sum(numeric_scores)
        record.number_of_evaluators = len(numeric_scores)
        record.average_score = record.total_score / record.number_of_evaluators if record.number_of_evaluators > 0 else 0.0
      else:
        record.total_score = 0.0
        record.average_score = 0.0
        record.number_of_evaluators = 0

  @api.model
  def create(self, vals):
    if 'criteria_id' in vals:
      criteria = self.env['ngsc.scoring.criteria'].browse(vals['criteria_id'])
      if criteria.type != 'point':
        raise ValidationError(
            "Chỉ được phép tạo tổng hợp cho tiêu chí loại 'Điểm'")

    return super(NGSCInnovationScoring, self).create(vals)

  @api.model
  def create_or_update_summary(self, idea_id, version_id, criteria_id):
    criteria = self.env['ngsc.scoring.criteria'].browse(criteria_id)

    if criteria.type != 'point':
      return False

    locked_summaries = self.env['ngsc.innovation.summary'].search([
      ('idea_id', '=', idea_id),
      ('version_id', '=', version_id),
      ('criteria_id', '=', criteria_id),
      ('is_latest', '=', True),
      ('status', '=', True)
    ])

    summary = self.search([
      ('idea_id', '=', idea_id),
      ('version_id', '=', version_id),
      ('criteria_id', '=', criteria_id)
    ], limit=1)

    if locked_summaries:
      total_score = sum(locked_summaries.mapped('score'))
      number_of_evaluators = len(locked_summaries)
      average_score = total_score / number_of_evaluators if number_of_evaluators > 0 else 0

      values = {
        'total_score': total_score,
        'number_of_evaluators': number_of_evaluators,
        'average_score': average_score,
      }

      if not summary:
        values.update({
          'idea_id': idea_id,
          'version_id': version_id,
          'criteria_id': criteria_id,
        })
        summary = self.create(values)
      else:
        summary.write(values)
    else:
      if summary:
        summary.write({
          'total_score': 0,
          'number_of_evaluators': 0,
          'average_score': 0,
        })

    return summary