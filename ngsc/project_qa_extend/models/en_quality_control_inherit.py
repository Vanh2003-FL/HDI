from odoo import models, fields, api, _


class QualityControlInherit(models.Model):
    _inherit = "en.quality.control"

    def _compute_pm_project(self):
        super(QualityControlInherit, self)._compute_pm_project()
        for rec in self:
            # Nếu QA cũ (en_project_qa_id) đã có và đủ điều kiện thì giữ nguyên
            if rec.is_pm_project:
                continue

            # Nếu QA cũ không có PM thì mới check QA mới
            if rec.project_id.en_project_qa_ids and self.env.user in rec.project_id.en_project_qa_ids:
                if rec.project_id.en_resource_id and rec.project_id.en_resource_id.order_line.filtered(
                        lambda x: x.employee_id.user_id == self.env.user
                ):
                    rec.is_pm_project = True

    @api.depends("project_id.en_resource_id")
    def _compute_edit_order_line(self):
        super(QualityControlInherit, self)._compute_edit_order_line()
        for rec in self:
            # Bổ sung logic cho QA mới
            if rec.project_id.en_project_qa_ids and self.env.user in rec.project_id.en_project_qa_ids:
                rec.edit_order_line = True

    @api.depends("project_id.en_resource_id", "project_id.mm_rate")
    def _compute_mm_qa_project(self):
        super(QualityControlInherit, self)._compute_mm_qa_project()
        for rec in self:
            total_md = 0
            if rec.project_id.en_resource_id:
                # Tính MM cho tất cả QA mới
                for line in rec.project_id.en_resource_id.order_line.filtered(
                        lambda x: x.employee_id.user_id in rec.project_id.en_project_qa_ids.mapped("id")
                ):
                    total_md += line.en_md
            if rec.mm_rate:
                rec.mm_qa_project += round(total_md / rec.mm_rate, 2)
