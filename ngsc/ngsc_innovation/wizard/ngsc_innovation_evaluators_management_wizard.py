# -*- coding: utf-8 -*-
from odoo import models, fields, api, _, exceptions
from odoo.exceptions import ValidationError, UserError


class NGSCInnovationEvaluatorsManagementWizard(models.TransientModel):
    _name = 'ngsc.innovation.evaluators.management.wizard'
    _description = 'TTNB Quản lý chấm điểm cho tất cả hội đồng đánh giá'

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
    evaluator_line_ids = fields.One2many(
        'ngsc.innovation.evaluators.management.line',
        'wizard_id',
        string='Danh sách hội đồng đánh giá'
    )

    @api.model
    def default_get(self, fields):
        res = super(NGSCInnovationEvaluatorsManagementWizard, self).default_get(
            fields)
        active_id = self.env.context.get('active_id')

        if active_id:
            idea = self.env['ngsc.innovation.idea'].browse(active_id)
            version = self.env['ngsc.innovation.version'].search([
                ('status', '=', True)
            ], limit=1, order='start_date desc')

            if not version:
                raise ValidationError("Không tìm thấy phiên bản áp dụng!")

            # Lấy danh sách hội đồng đánh giá
            try:
                evaluation_group = self.env.ref(
                    'ngsc_innovation.group_evaluation_board')
                evaluators = evaluation_group.users
            except:
                evaluators = self.env['res.users']

            evaluator_lines = []
            LineModel = self.env['ngsc.innovation.evaluators.management.line']
            for evaluator in evaluators:
                # Kiểm tra trạng thái chấm điểm
                locked_scores = self.env['ngsc.innovation.summary'].search([
                    ('idea_id', '=', idea.id),
                    ('evaluator_id', '=', evaluator.id),
                    ('is_latest', '=', True),
                    ('status', '=', True)
                ])

                has_scores = self.env['ngsc.innovation.summary'].search([
                    ('idea_id', '=', idea.id),
                    ('evaluator_id', '=', evaluator.id),
                    ('is_latest', '=', True)
                ])

                evaluator_line_vals = {
                    'wizard_id': self.id,
                    'evaluator_id': evaluator.id,
                    'evaluator_name': evaluator.name,
                    'has_scores': bool(has_scores),
                    'is_locked': bool(locked_scores),
                }
                line = LineModel.create(evaluator_line_vals)
                evaluator_lines.append(line.id)

            res.update({
                'idea_id': idea.id,
                'version_id': version.id,
                'evaluator_line_ids': [(6, 0, evaluator_lines)]
            })

        return res


class NGSCInnovationEvaluatorsManagementLine(models.TransientModel):
    _name = 'ngsc.innovation.evaluators.management.line'
    _description = 'Dòng quản lý hội đồng đánh giá'

    wizard_id = fields.Many2one(
        'ngsc.innovation.evaluators.management.wizard',
        string='Wizard'
    )
    evaluator_id = fields.Many2one(
        'res.users',
        string='Người chấm',
        required=True
    )
    evaluator_name = fields.Char(
        string='Tên người chấm',
        related='evaluator_id.name',
        store=True
    )
    has_scores = fields.Boolean(
        string='Đã chấm điểm',
        readonly=True
    )
    is_locked = fields.Boolean(
        string='Đã chốt điểm',
        readonly=True
    )
    status_display = fields.Char(
        string='Trạng thái',
        compute='_compute_status_display'
    )
    status_icon = fields.Html(
        string='Trạng thái',
        compute='_compute_status_icon'
    )

    @api.depends('has_scores', 'is_locked')
    def _compute_status_display(self):
        for rec in self:
            if rec.is_locked:
                rec.status_display = 'Đã chốt điểm'
            elif rec.has_scores:
                rec.status_display = 'Đã chấm điểm'
            else:
                rec.status_display = 'Chưa chấm điểm'

    @api.depends('has_scores', 'is_locked')
    def _compute_status_icon(self):
        for rec in self:
            if rec.is_locked:
                rec.status_icon = '<span class="badge badge-success">Đã chốt điểm</span>'
            elif rec.has_scores:
                rec.status_icon = '<span class="badge badge-info">Đã chấm điểm</span>'
            else:
                rec.status_icon = '<span class="badge badge-danger">Chưa chấm điểm</span>'

    def action_score_for_this_evaluator(self):
        """Mở form chấm điểm cho evaluator này"""
        self.ensure_one()

        if not self.env.user.has_group(
                'ngsc_innovation.group_internal_communication'):
            raise UserError('Bạn không có quyền chấm điểm thay.')

        # Sửa: Không tạo wizard ở đây, chỉ trả về action
        return {
            'name': f'Chấm điểm cho {self.evaluator_name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ngsc.innovation.ttnb.scoring.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_idea_id': self.wizard_id.idea_id.id,
                'default_version_id': self.wizard_id.version_id.id,
                'default_evaluator_id': self.evaluator_id.id,
            }
        }

    def action_view_scores_for_this_evaluator(self):
        """Xem điểm đã chấm của evaluator này (readonly)"""
        self.ensure_one()

        if not self.env.user.has_group(
                'ngsc_innovation.group_internal_communication'):
            raise UserError('Bạn không có quyền xem điểm.')

        # Sửa: Không tạo wizard ở đây, chỉ trả về action với context thích hợp
        return {
            'name': f'Xem điểm của {self.evaluator_name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ngsc.innovation.ttnb.scoring.wizard',
            'view_mode': 'form',
            'target': 'new',
            'flags': {'mode': 'readonly'},
            'context': {
                'default_idea_id': self.wizard_id.idea_id.id,
                'default_version_id': self.wizard_id.version_id.id,
                'default_evaluator_id': self.evaluator_id.id,
                'view_readonly': True,
            }
        }

    def action_edit_scores_for_this_evaluator(self):
        """Sửa điểm đã chấm của evaluator này (chỉ khi chưa chốt)"""
        self.ensure_one()

        if not self.env.user.has_group(
                'ngsc_innovation.group_internal_communication'):
            raise UserError('Bạn không có quyền sửa điểm.')

        if self.is_locked:
            raise UserError('Điểm đã được chốt, không thể sửa.')

        # Sửa: Không tạo wizard ở đây, chỉ trả về action với context thích hợp
        return {
            'name': f'Sửa điểm cho {self.evaluator_name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ngsc.innovation.ttnb.scoring.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_idea_id': self.wizard_id.idea_id.id,
                'default_version_id': self.wizard_id.version_id.id,
                'default_evaluator_id': self.evaluator_id.id,
                'edit_mode': True,
            }
        }
