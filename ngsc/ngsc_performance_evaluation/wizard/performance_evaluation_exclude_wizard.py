from odoo import fields, models, api


class PerformanceEvaluationExcludeWizard(models.TransientModel):
    _name = "performance.evaluation.exclude.wizard"
    _description = "Wizard chọn loại bỏ nhân sự đánh giá hiệu suất"

    exclude_id = fields.Many2one("ngsc.hr.performance.evaluation.exclude", string="Thông tin loại trừ")
    add_employee_ids = fields.Many2many("hr.employee", "exclude_add_employee_rel",
                                        "exclude_wizard_id", "employee_id", string="Nhân viên",
                                        domain=lambda
                                            self: "[('en_internal_ok', '=', True), ('id', 'in', {}),('id', 'not in', {})]".format(
                                            self._context.get('add_employee_ids', []),
                                            self._context.get('exclude_employee_ids', [])))
    exclude_employee_ids = fields.Many2many("ngsc.hr.performance.evaluation.exclude.detail",
                                            "exclude_exclude_employee_rel",
                                            "exclude_wizard_id", "exclude_detail_id", string="Nhân viên",
                                            domain=lambda self: "[('id', 'in', {})]".format(
                                                self._context.get('exclude_employee_ids', [])))

    def action_add(self):
        values = [
            (0, 0, {
                'exclude_id': self.exclude_id.id,
                'employee_id': emp.id,
                'work_email': emp.work_email,
            })
            for emp in self.add_employee_ids
        ]
        self.exclude_id.write({'exclude_employee_ids': values})

    def action_remove(self):
        self.exclude_employee_ids.unlink()
