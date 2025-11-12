from odoo import models, fields, api


class ProjectStatusReportInherit(models.Model):
    _inherit = "project.status.report"

    project_en_project_qa_ids = fields.Many2many(
        'res.users',
        'project_status_report_qa_rel',
        'report_id',
        'user_id',
        string='QA'
    )

    @api.model
    def _auto_init(self):
        """Migrate dữ liệu QA cũ sang Many2many nếu chưa có"""
        res = super()._auto_init()
        self.env.cr.execute("""
            INSERT INTO project_status_report_qa_rel (report_id, user_id)
            SELECT r.id, r.project_en_project_qa_id
            FROM project_status_report r
                     LEFT JOIN project_status_report_qa_rel rel
                               ON rel.report_id = r.id AND rel.user_id = r.project_en_project_qa_id
            WHERE r.project_en_project_qa_id IS NOT NULL
              AND rel.report_id IS NULL;
        """)
        return res

    @api.model
    def init_data(self):
        """Kế thừa logic gốc, bổ sung QA mới"""
        # Gọi logic gốc (chạy SQL insert + tính toán KPI)
        super(ProjectStatusReportInherit, self).init_data()

        # Sau khi gốc chạy xong, bổ sung QA mới
        date_from, date_to = self._get_date_range()
        reports = self.search([
            ('user_id', '=', self.env.user.id),
            ('project_date', '>=', date_from),
            ('project_date', '<=', date_to),
        ])

        for rec in reports:
            project = rec.project_id
            if not project:
                continue

            qa_user_ids = []
            if project.en_project_qa_id:
                # Nếu có QA cũ thì giữ nguyên
                qa_user_ids = [project.en_project_qa_id.id]
            elif hasattr(project, 'en_project_qa_ids') and project.en_project_qa_ids:
                # Nếu không có QA cũ thì fallback QA mới (m2m)
                qa_user_ids = project.en_project_qa_ids.ids

            if qa_user_ids:
                rec.project_en_project_qa_ids = [(6, 0, qa_user_ids)]

        return True

    def _get_date_range(self):
        """Hàm lấy khoảng thời gian từ context"""
        date_from_txt = self._context.get('date_from') or fields.Date.Date.context_today(self)
        date_to_txt = self._context.get('date_to') or fields.Date.Date.context_today(self)
        date_from = min(fields.Date.from_string(date_from_txt), fields.Date.from_string(date_to_txt))
        date_to = max(fields.Date.from_string(date_from_txt), fields.Date.from_string(date_to_txt))
        return date_from, date_to
