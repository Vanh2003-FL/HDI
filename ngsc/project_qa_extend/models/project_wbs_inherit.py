from odoo.exceptions import UserError

from odoo import fields, models, api


class ProjectWbs(models.Model):
    _inherit = 'en.wbs'

    is_project_qa = fields.Boolean(string="Là QA dự án", compute='_compute_is_project_qa')

    @api.depends("project_id")
    def _compute_is_project_qa(self):
        """User là QA nếu:
           - Là admin, hoặc
           - Nếu dự án có QA cũ thì user đó phải là QA cũ
           - Nếu dự án không có QA cũ thì user thuộc QA mới
        """
        current_user = self.env.user
        for rec in self:
            if not rec.project_id:
                rec.is_project_qa = False
                continue

            if current_user.has_group('base.group_system'):
                rec.is_project_qa = True
            else:
                # 🔹 Chỉ QA cũ được tính là QA hợp lệ
                rec.is_project_qa = (current_user == rec.project_id.en_project_qa_id)


    def button_sent_from_resource_planing(self):
        """Chỉ QA cũ hoặc admin mới được gửi duyệt"""
        # for rec in self:
        #     if not rec.is_project_qa:
        #         raise UserError("Chỉ QA chính hoặc admin mới có quyền gửi duyệt WBS!")
        return super().button_sent_from_resource_planing()

    def button_approved(self):
        """Chỉ QA cũ hoặc admin mới được duyệt"""
        # for rec in self:
        #     if not rec.is_project_qa:
        #         raise UserError("Chỉ QA chính hoặc admin mới có quyền duyệt WBS!")
        return super().button_approved()
