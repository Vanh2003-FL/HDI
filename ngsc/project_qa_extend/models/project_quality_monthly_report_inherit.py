# -*- coding: utf-8 -*-
import logging

from odoo import models, api

_logger = logging.getLogger(__name__)


class ProjectQualityMonthlyReportInherit(models.Model):
    _inherit = 'project.quality.monthly.report'

    @api.model
    def generate_monthly_report(self, start_month=None, end_month=None, project_code=None):
        """Kế thừa logic gốc, chỉ custom cách lấy QA"""
        # Gọi hàm gốc để tính toán, tạo/sửa báo cáo
        super_result = super().generate_monthly_report(start_month, end_month, project_code)

        # Sau khi chạy gốc xong, sửa lại field qa_name theo logic mới
        reports = self.search([])  # Có thể thêm domain theo tháng/dự án nếu muốn tối ưu
        for rec in reports:
            project = self.env['project.project'].search([('en_code', '=', rec.project_code)], limit=1)
            if not project:
                continue

            # Nếu có QA cũ thì giữ nguyên
            if project.en_project_qa_id:
                qa_str = project.en_project_qa_id.email or ''
            else:
                # Nếu không có QA cũ thì lấy QA mới (m2m)
                qa_emails = [user.email for user in project.en_project_qa_ids if user.email]
                qa_str = ", ".join(qa_emails) if qa_emails else ''

            if rec.qa_name != qa_str:
                rec.write({'qa_name': qa_str})

        return super_result
