from odoo import models, api


class ProjectCompletionQualityReportInherit(models.Model):
    _inherit = 'project.completion.quality.report'

    @api.model
    def generate_final_project_report(self, project_code=None):
        # Gọi logic gốc để tạo/cập nhật báo cáo
        super(ProjectCompletionQualityReportInherit, self).generate_final_project_report(project_code=project_code)

        # Sau khi gốc chạy xong, mình chỉ cần cập nhật lại QA cho các report
        domain = []
        if project_code:
            domain.append(('project_code', '=', project_code))

        reports = self.search(domain) if domain else self.search([])
        for report in reports:
            project = self.env['project.project'].search([('en_code', '=', report.project_code)], limit=1)
            if not project:
                continue

            # Nếu QA cũ rỗng → fallback sang QA mới
            if not report.qa_name:
                qa_emails = [qa.email for qa in project.en_project_qa_ids if qa.email]
                qa_emails_str = ', '.join(sorted(set(qa_emails)))
                if qa_emails_str:
                    report.qa_name = qa_emails_str
