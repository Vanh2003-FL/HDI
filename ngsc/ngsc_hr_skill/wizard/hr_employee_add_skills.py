from odoo import api, fields, models, _


class HrEmployeeAddSkills(models.TransientModel):
    _name = "hr.employee.add.skills"
    _description = "Wizard chọn nhiều kỹ năng nhân viên"

    hr_employee_id = fields.Many2one("hr.employee", string="Nhân viên")
    skill_ids = fields.Many2many("ngsc.competency.skill",
                                 "add_skills_hr_employee_rel", "add_skill_id", "hr_employee_id",
                                 string="Kỹ năng", required=True)
    skill_added_ids = fields.Many2many("ngsc.competency.skill", "added_skills_hr_employee_rel",
                                       "add_skill_id", "hr_employee_id", compute="_compute_skill_added",
                                       string="Kỹ năng đã thêm")

    @api.depends("hr_employee_id")
    def _compute_skill_added(self):
        for rec in self:
            rec.skill_added_ids = [(6, 0, rec.hr_employee_id.skill_ids.mapped('skill_id.id'))]

    def action_add_skills(self):
        if self.skill_ids:
            new_skill_ids = list(set(self.skill_ids.ids) - set(self.skill_added_ids.ids))
            values = [(0, 0, {"skill_id": skill_id}) for skill_id in new_skill_ids]
            self.hr_employee_id.write({'skill_ids': values})
