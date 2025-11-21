import logging

from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class ProjectDecision(models.Model):
    _inherit = 'project.decision'

    en_project_qa_ids = fields.Many2many(
        'res.users',
        'project_decision_qa_rel',
        'decision_id',
        'user_id',
        string='QA dự án'
    )

    @api.model
    def init(self):
        """Migrate dữ liệu QA cũ sang Many2many khi module được cài hoặc nâng cấp"""
        self.env.cr.execute("""
                            INSERT INTO project_decision_qa_rel (decision_id, user_id)
                            SELECT id, en_project_qa_id
                            FROM project_decision
                            WHERE en_project_qa_id IS NOT NULL ON CONFLICT (decision_id, user_id) DO NOTHING
                            """)

    @api.model
    def create(self, vals):
        """Tự động lấy QA từ dự án nếu chưa có QA"""
        # Lấy QA từ context nếu có
        if not vals.get('en_project_qa_ids'):
            default_qa_ids = self._context.get('default_en_project_qa_ids')
            if default_qa_ids:
                vals['en_project_qa_ids'] = [(6, 0, default_qa_ids)]
            elif vals.get('project_id'):
                # fallback: lấy QA từ project
                project = self.env['project.project'].browse(vals['project_id'])
                if project.en_project_qa_ids:
                    vals['en_project_qa_ids'] = [(6, 0, project.en_project_qa_ids.ids)]
        decision = super(ProjectDecision, self).create(vals)
        return decision
