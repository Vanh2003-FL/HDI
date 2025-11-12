from odoo import fields, models, api, _
from odoo.exceptions import UserError
import pytz
from datetime import datetime, timedelta, time


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    def button_approved(self):
        res = super().button_approved()
        if res:
            self.action_refresh_attendance()

    def button_mass_approved(self):
        super().button_mass_approved()
        self.action_refresh_attendance()

    def action_draft(self):
        super().action_draft()
        self.action_refresh_attendance()

    def action_refresh_attendance(self):
        for rec in self:
            attendances = self.env['hr.attendance'].sudo().search([('employee_id', 'in', rec.employee_id.ids), ('date', '>=', rec.request_date_from), ('date', '<=', rec.request_date_to), '|', ('en_soon', '=', True), ('en_late', '=', True)])
            attendances._get_en_soon()
            attendances._get_en_late()
            attendances._compute_color()
