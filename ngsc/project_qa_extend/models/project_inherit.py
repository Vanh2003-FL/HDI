from odoo import models, fields, api


class ProjectProject(models.Model):
    _inherit = 'project.project'

    en_project_qa_ids = fields.Many2many(
        comodel_name='res.users',
        relation='project_project_qa_users_rel',
        column1='project_id',  # Cột liên kết với project.project
        column2='user_id',  # Cột liên kết với res.users
        string='QA dự án',
        default=lambda self: self.env.user
    )

    @api.model
    def _auto_init(self):
        """Gọi khi khởi tạo field trong model, dùng để migrate SQL một lần."""
        res = super()._auto_init()

        # Migrate dữ liệu từ QA cũ nếu bản ghi chưa có trong QA mới
        self.env.cr.execute("""
                            INSERT INTO project_project_qa_users_rel (project_id, user_id)
                            SELECT p.id, p.en_project_qa_id
                            FROM project_project p
                                     LEFT JOIN project_project_qa_users_rel rel
                                               ON rel.project_id = p.id AND rel.user_id = p.en_project_qa_id
                            WHERE p.en_project_qa_id IS NOT NULL
                              AND rel.project_id IS NULL;
                            """)

        return res
    def button_create_project_decision(self):
        """Tạo quyết định và truyền QA từ dự án sang decision"""
        action = self.open_form_or_tree_view(
            'ngsc_project.project_decision_act',
            False,
            False,
            {'default_project_id': self.id, 'default_user_id': self.user_id.id},
            'Tạo QĐ TL Dự án'
        )
        action['views'] = [(False, 'form')]
        action['context'] = {
            'create': 0,
            'default_project_id': self.id,
            'default_user_id': self.user_id.id,
            'default_en_project_qa_ids': self.en_project_qa_ids.ids,
        }
        return action