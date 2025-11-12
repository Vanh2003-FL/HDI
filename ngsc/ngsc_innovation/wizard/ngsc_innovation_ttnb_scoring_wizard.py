# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError


class NGSCInnovationTTNBScoringWizard(models.TransientModel):
    _name = 'ngsc.innovation.ttnb.scoring.wizard'
    _description = 'TTNB Wizard chấm điểm thay cho hội đồng đánh giá'

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
        required=True
    )
    evaluator_name = fields.Char(
        string='Tên người chấm',
        related='evaluator_id.name',
        readonly=True
    )
    total_score = fields.Float(
        string='Tổng điểm',
        compute='_compute_total_score',
        store=True,
        help='Chỉ tính tổng điểm cho các tiêu chí loại point'
    )
    scoring_line_ids = fields.One2many(
        'ngsc.innovation.ttnb.scoring.wizard.line',
        'wizard_id',
        string='Chi tiết chấm điểm - chỉ tiêu chí loại point'
    )
    is_locked = fields.Boolean(
        string='Đã chốt điểm',
        compute='_compute_is_locked',
        store=False
    )

    view_readonly = fields.Boolean(
        string='Chế độ chỉ xem',
        default=False
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

    @api.depends('evaluator_id', 'idea_id')
    def _compute_is_locked(self):
        for rec in self:
            if rec.evaluator_id and rec.idea_id:
                locked_scores = self.env['ngsc.innovation.summary'].search([
                    ('idea_id', '=', rec.idea_id.id),
                    ('evaluator_id', '=', rec.evaluator_id.id),
                    ('is_latest', '=', True),
                    ('status', '=', True)
                ])
                rec.is_locked = bool(locked_scores)
            else:
                rec.is_locked = False

    @api.onchange('evaluator_id')
    def _onchange_evaluator_id(self):
        if self.evaluator_id and self.idea_id and self.version_id:
            self._load_scoring_lines()

    def _load_scoring_lines(self):
        if not (self.evaluator_id and self.idea_id and self.version_id):
            return

        criteria_list = self.env['ngsc.scoring.criteria'].search([
            ('version_id', '=', self.version_id.id),
            ('type', '=', 'point')
        ])

        scoring_lines = []
        for criteria in criteria_list:
            existing_score = self.env['ngsc.innovation.summary'].search([
                ('idea_id', '=', self.idea_id.id),
                ('criteria_id', '=', criteria.id),
                ('evaluator_id', '=', self.evaluator_id.id),
                ('version_id', '=', self.version_id.id),
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

        self.scoring_line_ids = [(5, 0, 0)] + scoring_lines

    @api.model
    def default_get(self, fields):
        res = super(NGSCInnovationTTNBScoringWizard, self).default_get(fields)

        # Kiểm tra context để set readonly mode
        if self.env.context.get('view_readonly'):
            res['view_readonly'] = True

        # Lấy thông tin từ context
        idea_id = self.env.context.get('default_idea_id')
        version_id = self.env.context.get('default_version_id')
        evaluator_id = self.env.context.get('default_evaluator_id')

        if idea_id and version_id:
            idea = self.env['ngsc.innovation.idea'].browse(idea_id)
            version = self.env['ngsc.innovation.version'].browse(version_id)

            res.update({
                'idea_id': idea.id,
                'version_id': version.id,
            })

            if evaluator_id:
                res['evaluator_id'] = evaluator_id

                # Load scoring lines
                criteria_list = self.env['ngsc.scoring.criteria'].search([
                    ('version_id', '=', version_id),
                    ('type', '=', 'point')
                ])

                scoring_lines = []
                for criteria in criteria_list:
                    existing_score = self.env['ngsc.innovation.summary'].search([
                        ('idea_id', '=', idea_id),
                        ('criteria_id', '=', criteria.id),
                        ('evaluator_id', '=', evaluator_id),
                        ('version_id', '=', version_id),
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

                res['scoring_line_ids'] = scoring_lines

        return res

    def action_back_to_management(self):
        """Quay lại popup quản lý evaluator mà KHÔNG lưu gì"""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ngsc.innovation.evaluators.management.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_id': self.idea_id.id,
            },
        }

    def action_submit_scores(self):
        self.ensure_one()

        if not self.env.user.has_group(
                'ngsc_innovation.group_internal_communication'):
            raise UserError('Bạn không có quyền chấm điểm thay.')

        if not self.evaluator_id:
            raise ValidationError('Vui lòng chọn người chấm điểm.')

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

                    if line.score_point is False:
                        raise ValidationError(f"Bạn phải nhập điểm cho tiêu chí '{line.criteria_name}'")

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
                    'message': f'Đã lưu điểm chấm cho {self.evaluator_name} thành công!',
                    'type': 'success',
                    'sticky': False,
                }
            }

        except Exception as e:
            raise ValidationError(f"Lỗi khi lưu điểm: {str(e)}")

    def action_lock_scores(self):
        self.ensure_one()

        if not self.env.user.has_group(
                'ngsc_innovation.group_internal_communication'):
            raise UserError('Bạn không có quyền chốt điểm thay.')

        if not self.evaluator_id:
            raise ValidationError('Vui lòng chọn người chấm điểm.')

        evaluator_scores = self.env['ngsc.innovation.summary'].search([
            ('idea_id', '=', self.idea_id.id),
            ('evaluator_id', '=', self.evaluator_id.id),
            ('is_latest', '=', True)
        ])

        if not evaluator_scores:
            raise UserError(f'{self.evaluator_name} chưa chấm điểm, không thể chốt.')

        if evaluator_scores.filtered(lambda r: r.status):
            raise UserError(f'{self.evaluator_name} đã chốt điểm rồi.')

        evaluator_scores.write({'status': True})

        ScoringModel = self.env['ngsc.innovation.scoring'].sudo()
        for score_record in evaluator_scores:
            if score_record.criteria_id.type == 'point':
                self._update_scoring_summary(score_record.criteria_id.id, ScoringModel)

        self.idea_id.message_post(
            body=f'TTNB đã chốt điểm thay cho {self.evaluator_name}.'
        )

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ngsc.innovation.evaluators.management.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_id': self.idea_id.id,
            }
        }

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

        scoring = ScoringModel.search([
            ('idea_id', '=', self.idea_id.id),
            ('version_id', '=', self.version_id.id),
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

            if scoring:
                scoring.write(values)
            else:
                values.update({
                    'idea_id': self.idea_id.id,
                    'version_id': self.version_id.id,
                    'criteria_id': criteria_id,
                })
                ScoringModel.create(values)
        else:
            if scoring:
                scoring.write({
                    'total_score': 0,
                    'number_of_evaluators': 0,
                    'average_score': 0,
                })

        return True


class NGSCInnovationTTNBScoringWizardLine(models.TransientModel):
    _name = 'ngsc.innovation.ttnb.scoring.wizard.line'
    _description = 'Chi tiết chấm điểm TTNB - chỉ cho tiêu chí loại point'

    wizard_id = fields.Many2one(
        'ngsc.innovation.ttnb.scoring.wizard',
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
        help='Điểm chấm cho tiêu chí'
    )

    @api.constrains('criteria_id')
    def _check_criteria_type(self):
        for rec in self:
            if rec.criteria_id.type != 'point':
                raise ValidationError(
                    "Chỉ được phép chấm điểm cho tiêu chí loại 'Điểm'")
