# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class ProjectTask(models.Model):
    _inherit = ['project.task']


    @api.constrains("stage_id")
    def _constrains_stage_id(self):
        for r in self:
            if r.stage_id.en_mark not in ['b', 'a'] and r.en_task_position.state != 'ongoing':
                raise ValidationError(
                    'Gói việc chưa bật trạng thái "Đang thực hiện", người dùng cần liên hệ Người yêu cầu của Công việc để cập nhật')
            tasks = r.en_task_position.task_ids.filtered(lambda x: x.stage_id.en_mark != 'b')
            if not tasks.filtered(lambda x: x.stage_id.en_mark != 'g'):
                try:
                    r._sent_email()
                except Exception as e:
                    # Log lỗi nhưng không rollback transaction
                    _logger.warning(f"Không thể gửi email thông báo: {str(e)}")
                    # Thông báo cho user nếu có method notify_danger
                    if hasattr(r.env.user, 'notify_danger'):
                        r.env.user.notify_danger(message=f"Không thể gửi email thông báo: {str(e)}")

    def _sent_email(self):
        template = self.env.ref('ngsc_project.email_template_project_task_complete')
        if template:
            # Gửi email với template
            template.send_mail(self.id, force_send=True)

    # @api.constrains('en_task_position', 'en_task_position.date_start', 'en_task_position.date_end')
    # def _constrains_task_positions(self):
    #     self._en_constrains_start_deadline_date()