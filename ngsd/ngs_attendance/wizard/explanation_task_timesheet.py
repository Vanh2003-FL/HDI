from odoo import models, fields, api, _, exceptions

from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)


class ExplanationTaskTimesheet(models.TransientModel):
    _name = 'explanation.task.timesheet'
    _description = 'Tạo timesheet giải trình'

    explanation_id = fields.Many2one('hr.attendance.explanation', string="Giải trình chấm công", readonly=True, copy=False)
    user_id = fields.Many2one(related='explanation_id.employee_id.user_id')

    project_id = fields.Many2one('project.project', string="Dự án")
    task_id = fields.Many2one('project.task', string="Công việc", domain="[('project_id', '=', project_id), ('en_wbs_state', '=', 'approved'), ('en_handler', '=', user_id)]")

    en_nonproject_task_id = fields.Many2one('en.nonproject.task', string='Công việc ngoài dự án', domain="[('en_pic_id', '=', user_id)]")

    type = fields.Char()

    def button_confirm(self):
        context = {
            "default_date": self.explanation_id.explanation_date,
            "default_user_id": self.explanation_id.employee_id.user_id.id,
            "default_employee_id": self.explanation_id.employee_id.id,
            "default_explanation_id": self.explanation_id.id,
            "timesheet_from_explanation": True,
        }
        if self.type == 'TSDA' and self.task_id:
            context.update({
                "default_project_id": self.project_id.id,
                "default_task_id": self.task_id.id,
            })
            return {
                'name': 'Tạo timesheet',
                'view_mode': 'form',
                'res_model': 'account.analytic.line',
                'type': 'ir.actions.act_window',
                'context': context,
                'target': 'new',
                'views': [(self.env.ref('ngs_attendance.ts_giai_trinh_da_hr_timesheet_line_form').id, 'form')],
            }
        if self.type == 'TSNDA' and self.en_nonproject_task_id:
            context.update({
                "default_en_nonproject_task_id": self.en_nonproject_task_id.id,
            })
            return {
                'name': 'Tạo timesheet',
                'view_mode': 'form',
                'res_model': 'account.analytic.line',
                'type': 'ir.actions.act_window',
                'context': context,
                'target': 'new',
                'views': [(self.env.ref('ngs_attendance.ts_giai_trinh_nda_hr_timesheet_line_form').id, 'form')],
            }
        return
