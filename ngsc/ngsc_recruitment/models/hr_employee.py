from odoo import models, api


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    @api.onchange('department_id')
    def _onchange_en_department_id(self):
        if self.env.context.get('default_department_id'):
            return
        for rec in self:
            rec.en_department_id = False

    @api.onchange('en_area_id')
    def _onchange_en_area_id(self):
        if self.env.context.get('default_en_area_id'):
            return
        for rec in self:
            rec.en_block_id = False

    @api.onchange('en_block_id')
    def _onchange_en_block_id(self):
        if self.env.context.get('default_en_block_id'):
            return
        for rec in self:
            rec.department_id = False

