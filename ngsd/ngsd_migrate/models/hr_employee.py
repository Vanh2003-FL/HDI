from odoo import models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def check_required_field(self):
        return False
