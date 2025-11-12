from odoo import fields, models, api
from odoo.exceptions import UserError
from odoo.addons.approvals.models.approval_category import CATEGORY_SELECTION


class ApprovalCategory(models.Model):
    _inherit = 'approval.category'

    approval_type = fields.Selection(selection_add=[('car', 'Xe'), ('business', 'Công tác'), ('vpp', 'VPP'), ('new_asset', 'Cấp TSCĐ'), ('old_asset', 'Sửa chữa TSCĐ'), ('person_asset', 'Đăng ký sử dụng TSCN')], string='Loại', required=1, ondelete={'car': 'cascade', 'business': 'cascade', 'vpp': 'cascade', 'new_asset': 'cascade', 'old_asset': 'cascade', 'person_asset': 'cascade'})
    has_job = fields.Selection(CATEGORY_SELECTION, string="Chức vụ", default="no", required=True)
    has_department = fields.Selection(CATEGORY_SELECTION, string="Phòng", default="no", required=True)
    has_phone = fields.Selection(CATEGORY_SELECTION, string="Số điện thoại", default="no", required=True)
    has_hr_department = fields.Selection(CATEGORY_SELECTION, string="Trung tâm/Ban", default="no", required=True)
    has_hr_user = fields.Selection(CATEGORY_SELECTION, string="HCNS phụ trách", default="no", required=True)
    has_expected_return_date = fields.Selection(CATEGORY_SELECTION, string="Hạn trả dự kiến", default="no", required=True)
    has_actual_return_date = fields.Selection(CATEGORY_SELECTION, string="Ngày trả thực tế", default="no", required=True)

    def create_request(self):
        res = super().create_request()
        if self.approval_type in ['new_asset', 'old_asset', 'person_asset']:
            action = self.env["ir.actions.actions"]._for_xml_id("ngs_e_office.account_asset_request_action_all")
            action['context'] = res['context']
            action['context']['default_name'] = False
            action['views'] = [[self.env.ref('ngs_e_office.ngs_approval_request_asset_view_form').id, "form"]]
            action['view_mode'] = 'form'
            return action
        return res

    def action_request(self):
        if self.approval_type in ['new_asset', 'old_asset', 'person_asset']:
            action = self.env["ir.actions.actions"]._for_xml_id("ngs_e_office.account_asset_request_action_all")
        else:
            action = self.env["ir.actions.actions"]._for_xml_id("ngs_e_office.approval_request_action_all")
        return action
