from odoo import models, api, fields


class ChangeTaskTimesheet(models.TransientModel):
    _inherit = "change.task.timesheet"

    task_id = fields.Many2one(
        domain="[('category', '=', 'task'),('project_id', '=', project_id), ('project_wbs_state', '=', 'approved')]")
