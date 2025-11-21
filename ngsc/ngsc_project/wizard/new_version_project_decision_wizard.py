from odoo import models, fields, _


class NewVersionProjectDecisionWizard(models.TransientModel):
    _name = "new.version.project.decision.wizard"
    _description = "New Version Project Decision Wizard"

    project_decision_id = fields.Many2one('project.decision')
    name = fields.Char(string="Message", readonly=True, default='Bạn đang tạo mới phiên bản QĐ TL Dự án, thông tin sẽ được cập nhật theo thông tin hiện tại của Dự án?')

    def button_confirm(self):
        return self.project_decision_id.button_duplicate_project_decision()

    def button_refuse(self):
        return self.project_decision_id.button_duplicate_project_decision_no_vals()
