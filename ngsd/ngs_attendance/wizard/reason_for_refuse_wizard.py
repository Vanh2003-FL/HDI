from odoo import models, fields, api, _

class ReasonForRefuseWizard(models.TransientModel):
    _name = 'reason.for.refuse.wizard'
    _description = 'lý do từ chối'


    hr_attendance_explanation_id = fields.Many2one(comodel_name='hr.attendance.explanation', string='lý do giải trình', required=True)
    reason = fields.Char(string='Lý do từ chối', required=True)

    def action_confirm(self):
        for rec in self:
            rec.hr_attendance_explanation_id.write({
                'state': 'refuse',
                'reason_for_refuse': rec.reason,
            })
            rec.hr_attendance_explanation_id.send_notify('Bản ghi giải trình của bạn đã bị từ chối. Vui lòng bấm tại đây để xem chi tiết.', self.hr_attendance_explanation_id.employee_id.user_id)
            approver = rec.hr_attendance_explanation_id.mapped('approver_ids').filtered(lambda approver: approver.user_id == self.env.user)
            approver.write({'status': 'refused'})
