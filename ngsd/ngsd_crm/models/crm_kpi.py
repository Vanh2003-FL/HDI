from odoo import api, fields, models, Command, _
from odoo.exceptions import UserError, ValidationError


class CRMKpi(models.Model):
    _name = 'crm.kpi'
    _description = 'Chỉ tiêu'

    type = fields.Selection(selection=[('year', 'Theo năm'), ('quarter', 'Theo quý'), ('month', 'Theo tháng')], string="Loại chỉ tiêu", required=True)
    start_date = fields.Date(required=True, string="Áp dụng từ ngày")
    end_date = fields.Date(required=True, string="Áp dụng đến ngày")
    targets_amount = fields.Float(required=True, string="Chỉ tiêu doanh thu", default=0)
    department_ids = fields.Many2many('hr.department', string="Bộ phận thực hiện")
    employee_ids = fields.Many2many('hr.employee', string="Nhân viên thực hiện")

    def add_target_emp(self):
        if self.type:
            self.employee_ids.write({
                f'target_{self.type}': self.targets_amount,
                f'start_date_{self.type}': self.start_date,
                f'end_date_{self.type}': self.end_date
            })
