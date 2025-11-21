# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ResUsersInherit(models.Model):
    _inherit = "res.users"

    # Giữ nguyên field, chỉ bổ sung compute (gọi super trước rồi hợp nhất thêm từ en_project_qa_ids)
    technical_field_28159 = fields.Many2many(
        string='🐧',
        comodel_name='hr.employee',
        compute='_compute_technical_field_28159',
    )

    @api.depends('employee_id')
    def _compute_technical_field_28159(self):
        """Mở rộng compute:
        1) Gọi logic gốc (dựa en_project_qa_id)
        2) Bổ sung nhân sự từ các dự án mà user là QA (Many2many: en_project_qa_ids)
        """
        # --- 1) logic gốc ---
        super(ResUsersInherit, self)._compute_technical_field_28159()

        # --- 2) cộng thêm từ QA M2M ---
        Project = self.env['project.project']
        for rec in self:
            # Tìm các dự án mà user là QA (M2M)
            projects_m2m = Project.search([('en_project_qa_ids', 'in', rec.id)])
            # Lấy nhân sự từ resource planning của dự án
            extra_employees = projects_m2m.en_resource_id.order_line.mapped('employee_id')
            # Hợp nhất với kết quả từ logic cũ (loại trùng bằng toán tử '|')
            rec.technical_field_28159 = (rec.technical_field_28159 | extra_employees)


class ResGroupsInherit(models.Model):
    _inherit = "res.groups"

    @api.model
    def get_application_groups(self, domain):
        domain = list(domain or [])
        user_ngsd_categ = self.env.ref('ngsd_base.user_ngsd_categ', raise_if_not_found=False)
        if user_ngsd_categ:
            domain += [('category_id', '!=', user_ngsd_categ.id)]

        group_account_user = self.env.ref('account.group_account_user', raise_if_not_found=False)
        if group_account_user and group_account_user.category_id.xml_id == 'base.module_category_hidden':
            domain += [('id', '!=', group_account_user.id)]

        return super().get_application_groups(domain)
