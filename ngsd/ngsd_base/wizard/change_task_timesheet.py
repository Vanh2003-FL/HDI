from odoo import models, api, fields, _, exceptions

from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)


class ChangeTaskTimesheet(models.TransientModel):
    _name = 'change.task.timesheet'
    _description = 'Chuyển timesheet'

    timesheet_ids = fields.Many2many('account.analytic.line', string='Timesheets')
    project_id = fields.Many2one('project.project', string="Dự án")
    task_id = fields.Many2one('project.task', string="Công việc", domain="[('project_id', '=', project_id), ('en_wbs_state', '=', 'approved')]", required=1)

    def button_confirm(self):
        for line in self.timesheet_ids.sudo():
            line.write({
                'task_id': self.task_id.id,
                'en_nonproject_task_id': False,
            })
            line.ot_id.write({
                'task_id': self.task_id.id,
                'en_nonproject_task_id': False,
            })
            line.ot_id.en_overtime_plan_id.write({
                'en_work_id': self.task_id.id,
                'en_project_id': self.task_id.project_id.id,
                'en_work_nonproject_id': False,
                'en_work_inproject': True,
            })
        return {'type': 'ir.actions.act_window_close'}
