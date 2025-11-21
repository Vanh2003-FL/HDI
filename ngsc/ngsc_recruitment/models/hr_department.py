from odoo import models, fields, api, _


class HrDepartment(models.Model):
    _inherit = "hr.department"

    talent_acquisition = fields.Many2one(
        "hr.employee",
        string="TA phụ trách",
        domain="[('en_department_id.code', '=', 'ĐBNL')]"
    )
