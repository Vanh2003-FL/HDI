# -*- coding: utf-8 -*-
import json
import ast
from lxml import etree
from odoo import models, fields, api, _

readonly_fields = {
    'name', 'image_1920', 'state_hr_employee', 'en_type_id',
    'barcode', 'work_email', 'en_area_id', 'en_block_id',
    'department_id', 'en_department_id', 'job_id',
    'en_level_id', 'en_technique', 'en_date_start', 'contract_id'
}


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    skill_ids = fields.One2many('hr.employee.skills', 'hr_employee_id', string=u'Thông tin năng lực')
    is_readonly_fields_hr = fields.Boolean(string="Không được sửa thông tin nhân sự",
                                           compute="_compute_is_readonly_allowed", default=False)
    is_allowed_add_skill = fields.Boolean(string="Được phép thêm đánh giá năng lực",
                                          compute="_compute_is_readonly_allowed", default=True)

    def _compute_is_readonly_allowed(self):
        current_user = self.env.user
        groups_allowed = self.env.user.has_group('ngsd_base.group_cbf,base.group_system')
        groups_competency_allowed = self.env.user.has_group('ngsc_competency.group_competency_od')
        for rec in self:
            readonly = False
            if rec.en_internal_ok:
                readonly = rec.user_id == current_user or (rec.user_id != current_user and not groups_allowed)
            rec.is_readonly_fields_hr = readonly
            rec.is_allowed_add_skill = rec.user_id == current_user or groups_competency_allowed

    def action_open_wizard_add_skills(self):
        return {
            'name': "Thêm kỹ năng",
            'view_mode': 'form',
            'res_model': 'hr.employee.add.skills',
            'type': 'ir.actions.act_window',
            'view_id': self.env.ref('ngsc_hr_skill.hr_employee_add_skills_form_view').id,
            'views': [(self.env.ref('ngsc_hr_skill.hr_employee_add_skills_form_view').id, 'form')],
            'context': {'default_hr_employee_id': self.id},
            'target': 'new',
        }


    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super().fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if view_type != 'form':
            return res
        doc = etree.XML(res['arch'])
        readonly_condition = ["is_readonly_fields_hr", "=", True]
        for field_name in readonly_fields:
            for node in doc.xpath(f"//field[@name='{field_name}']"):
                modifiers = json.loads(node.get('modifiers', '{}'))
                old_readonly = modifiers.get('readonly')
                if 'readonly' in modifiers:
                    if isinstance(old_readonly, str):
                        try:
                            old_readonly = ast.literal_eval(old_readonly)
                        except Exception as e:
                            print("Exception", e)
                            old_readonly = []
                    modifiers['readonly'] = ['|', readonly_condition] + old_readonly
                else:
                    modifiers['readonly'] = [readonly_condition]
                node.set('modifiers', json.dumps(modifiers))
        res['arch'] = etree.tostring(doc, encoding='unicode')
        return res