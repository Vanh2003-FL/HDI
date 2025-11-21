from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    @api.model
    def create(self, values):
        # Cho phép gửi email invitation odoo khi import
        if self._context.get("import_file"):
            self = self.with_context(install_mode=False, import_file=False)
        return super(HrEmployee, self).create(values)
