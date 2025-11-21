from odoo import models, fields, api, _


class ApprovalApprover(models.Model):
    _inherit = "approval.approver"

    hr_attendance_explanation_id = fields.Many2one('hr.attendance.explanation', string="Giải trình chấm công")
    company_id = fields.Many2one(comodel_name='res.company', related=False, default=lambda self: self.env.company)
    sequence = fields.Integer("Trình tự")
