import re

from odoo import models, api


class FinalProjectCompletionQualityReportInherit(models.AbstractModel):
    _inherit = "final.project.completion.quality.report"

    @api.model
    def _get_lines(self, options, line_id=None):
        # Gọi logic gốc
        lines = super()._get_lines(options, line_id)

        # Bổ sung logic: thay đổi cột QA
        for line in lines:
            # Đảm bảo đủ cột, và cột QA đang ở index 6 (theo code gốc)
            if len(line.get("columns", [])) > 6:
                project_code = line["columns"][3]["name"]  # cột mã dự án
                project = self.env["project.project"].search([("en_code", "=", project_code)], limit=1)
                if project:
                    # Lấy danh sách QA mới từ en_project_qa_ids
                    new_qas = [
                        re.sub(r"@.*$", "", user.email) for user in project.en_project_qa_ids if user.email
                    ]
                    new_qas = sorted(set(q for q in new_qas if q))  # loại bỏ trùng & rỗng
                    if new_qas:
                        line["columns"][6]["name"] = ", ".join(new_qas)

        return lines
