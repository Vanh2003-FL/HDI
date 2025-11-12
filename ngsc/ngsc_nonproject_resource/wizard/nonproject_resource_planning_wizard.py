from odoo import fields, models, api


class NonprojectResourcePlanningWizard(models.TransientModel):
    _name = "nonproject.resource.planning.wizard"
    _description = "Wizard chọn loại bỏ nhân sự đánh giá hiệu suất"

    exclude_id = fields.Many2one("nonproject.resource.planning.exclude", string="Thông tin loại trừ")
    add_employee_ids = fields.Many2many("hr.employee", "nonproject_wizard_add_employee_rel",
                                        "exclude_wizard_id", "employee_id", string="Nhân viên",
                                        domain=lambda
                                            self: "[('en_internal_ok', '=', True),('id', 'not in', {})]".format(
                                            self._context.get('add_employee_ids', []),
                                            self._context.get('exclude_employee_ids', [])))
    exclude_employee_ids = fields.Many2many("nonproject.resource.planning.exclude.detail",
                                            "nonproject_wizard_exclude_employee_rel",
                                            "exclude_wizard_id", "exclude_detail_id", string="Nhân viên",
                                            domain=lambda self: "[('id', 'in', {})]".format(
                                                self._context.get('exclude_employee_ids', [])))

    def action_add(self):
        values = [
            (0, 0, {
                'exclude_id': self.exclude_id.id,
                'employee_id': emp.id,
            })
            for emp in self.add_employee_ids
        ]
        self.exclude_id.write({'exclude_employee_ids': values})

    def action_remove(self):
        self.exclude_employee_ids.unlink()
