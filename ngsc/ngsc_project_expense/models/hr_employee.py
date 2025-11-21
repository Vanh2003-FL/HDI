from odoo import models, fields, api, _, exceptions
from odoo.exceptions import ValidationError, UserError, AccessError



class Employee(models.Model):
    _inherit = "hr.employee"

    is_os = fields.Boolean(string="OS", related="en_type_id.is_os", groups="hr.group_hr_user", store=True)
    history_level_ids = fields.One2many("history.level", "employee_id", string="Lịch sử cấp bậc")
    os_expense_ids = fields.One2many("os.expense", "employee_id", string="Chi phí OS")