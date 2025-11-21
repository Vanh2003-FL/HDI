from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _


class RemindEvaluationWizard(models.TransientModel):
    _name = "remind.evaluation.wizard"
    _description = "Nhắc nhở hoàn thành đánh giá"

    evaluation_type = fields.Selection(string="Loại đánh giá", required=True,
                               selection=[('performance_evaluation', 'Đánh giá hiệu suất'),
                                           ('task_evaluation', 'Đánh giá chất lượng công việc')])
    deadline = fields.Date(string="Hạn hoàn thành", required=True)

    def action_remind_evaluation(self):
        if self.evaluation_type == 'performance_evaluation':
            self.action_send_mail_performance_evaluation()
        elif self.evaluation_type == 'task_evaluation':
            self.action_send_mail_task_evaluation()
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_send_mail_performance_evaluation(self):
        active_ids = self.env.context.get('active_ids') or []
        if active_ids:
            records = self.env['ngsc.hr.performance.evaluation'].browse(active_ids)
        else:
            today = fields.Date.Date.context_today(self)
            first_day_of_month = today + relativedelta(day=1, months=-1)
            records = self.env["ngsc.hr.performance.evaluation"].search([
                ("date", "=", first_day_of_month),
                ("state", "in", ['new', 'evaluated_again']),
            ])

        records = records.filtered(lambda r: r.direct_manager_id and r.direct_manager_id.email and r.state in ['new', 'evaluated_again'])
        if not records:
            return

        mail_template = self.env.ref(
            'ngsc_performance_evaluation.performance_remind_evaluation_mail_template'
        )
        deadline = datetime.strftime(self.deadline, '%d/%m/%Y')
        managers = records.mapped("direct_manager_id")

        for manager in managers:
            recs = records.filtered(lambda r: r.direct_manager_id.id == manager.id)
            if not recs:
                continue
            ctx = {"deadline": deadline, "evaluations": recs}
            mail_template.write({"email_to": manager.email})
            mail_template.with_context(ctx).send_mail(recs[0].id, force_send=True)
            mail_template.write({"email_to": False})

    def action_send_mail_task_evaluation(self):
        active_ids = self.env.context.get('active_ids') or []
        if active_ids:
            records = self.env['task.evaluation'].browse(active_ids)
        else:
            today = fields.Date.Date.context_today(self)
            first_day_of_month = today + relativedelta(day=1, months=-1)
            records = self.env["task.evaluation"].search([
                ("date_evaluation", "=", first_day_of_month),
                ("state", "in", ['not_evaluated', 'evaluated_again']),
                ("is_locked", "=", False),
            ])

        records = records.filtered(lambda r: r.reviewer_id and r.reviewer_id.email and r.state in ['not_evaluated', 'evaluated_again'])
        if not records:
            return

        mail_template = self.env.ref(
            'ngsc_performance_evaluation.task_remind_evaluation_mail_template'
        )
        deadline = datetime.strftime(self.deadline, '%d/%m/%Y')
        reviewers = records.mapped("reviewer_id")

        for reviewer in reviewers:
            recs = records.filtered(lambda r: r.reviewer_id.id == reviewer.id)
            if not recs:
                continue
            ctx = {"deadline": deadline, "tasks": recs}
            mail_template.write({"email_to": reviewer.email})
            mail_template.with_context(ctx).send_mail(recs[0].id, force_send=True)
            mail_template.write({"email_to": False})