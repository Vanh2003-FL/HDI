from odoo import api, fields, models


class EnHrOvertime(models.Model):
    _inherit = "en.hr.overtime"

    approved_overtime_date = fields.Date(string="Thời gian phê duyệt", index=True)

    def button_approved(self):
        super().button_approved()
        today = fields.Date.Date.context_today(self)
        for rec in self:
            if rec.state == "approved":
                rec.sudo().write({'approved_overtime_date': today})