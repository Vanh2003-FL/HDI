from odoo import models, fields, _


class NewVersionWBSWizard(models.TransientModel):
    _name = "new.version.wbs.wizard"
    _description = "New Version WBS Wizard"

    wbs_id = fields.Many2one('en.wbs')
    name = fields.Char(string="Message", readonly=True, default='Bạn đang tạo mới phiên bản WBS bao gồm Giai đoạn, Gói công việc, Công việc giống như phiên bản hiện tại?')

    def button_confirm(self):
        return self.wbs_id.button_duplicate_wbs()

    def button_refuse(self):
        return self.wbs_id.button_duplicate_wbs_no_vals()
