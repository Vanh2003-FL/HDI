from odoo import models, fields, _


class NgscInnovationRejectWizard(models.TransientModel):
    _name = 'ngsc.innovation.reject.wizard'
    _description = 'Lý do từ chối ý tưởng'

    reason = fields.Text(string="Lý do từ chối", required=True)

    def action_confirm_reject(self):
        """Xác nhận từ chối ý tưởng và lưu lý do"""
        idea = self.env['ngsc.innovation.idea'].browse(self.env.context.get('active_id'))
        if idea:
            idea.action_reject(reason=self.reason)
        return {'type': 'ir.actions.act_window_close'}
