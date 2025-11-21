from odoo import api, fields, models, tools, _


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    def _filter_visible_menus(self):
        res = super()._filter_visible_menus()

        ncs_company = self.env['res.company'].search([('company_type', '=', 'ncs')], limit=1).id
        allowed_company_ids = self.env.user.company_ids.ids
        if allowed_company_ids == [ncs_company]:
            no_ncs = [
                self.env.ref("ngsd_menu.supplier_menu").id,
                self.env.ref("ngsd_menu.competitors_menu").id,
                self.env.ref("ngsd_menu.manufacturer_menu").id,
                self.env.ref("ngsd_menu.crm_atta_action_menu").id,
                self.env.ref("ngsd_menu.crm_noti_not_target").id,
                self.env.ref("ngsd_menu.crm_kpi_action_menu").id,
                self.env.ref("ngsd_menu.crm_support_state_menu").id,
            ]
            return res.filtered(lambda x: x.id not in no_ncs)
        if ncs_company not in allowed_company_ids:
            only_ncs = [
                self.env.ref("ngsd_menu.x_customer_category_menu").id,
                self.env.ref("ngsd_menu.x_customer_group_menu").id,
                self.env.ref("ngsd_menu.kt_department_menu").id,
                self.env.ref("ngsd_menu.project_type_source_menu").id,
                self.env.ref("ngsd_menu.x_legal_menu").id,
            ]
            return res.filtered(lambda x: x.id not in only_ncs)
        return res
