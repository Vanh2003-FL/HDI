from odoo import models, api, _, exceptions
from odoo.exceptions import ValidationError


class EnWorkpackage(models.Model):
    _inherit = 'en.workpackage'

    def write(self, vals):
        res = super().write(vals)
        for record in self:
            if 'state' in vals and record.state == 'ongoing':
                if record.project_stage_id.state == 'draft':
                    record.project_stage_id.sudo().write({'state': 'ongoing'})
            if 'state' in vals:
                work_packages = record.project_stage_id.order_line.filtered(lambda x: x.state != 'cancel')
                if work_packages and not work_packages.filtered(lambda x: x.state != 'done'):
                    record._sent_email()
        return res

    def _sent_email(self):
        template = self.env.ref('ngsc_project.email_template_en_workpackage_complete')
        if template:
            # Gửi email với template
            try:
                template.send_mail(self.id, force_send=True)
            except Exception as e:
                # Không raise ValidationError nữa, chỉ notify
                self.env.user.notify_danger(message="Không thể gửi email thông báo: %s" % str(e))

    @api.constrains('date_start', 'date_end')
    def _constrains_task_positions(self):
        self.task_ids._en_constrains_start_deadline_date()