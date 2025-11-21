from odoo import models, fields, api, _


class ChangeTaskTimesheet(models.TransientModel):
    _inherit = "change.task.timesheet"

    task_id = fields.Many2one(
        domain="[('category', '=', 'task'),('project_id', '=', project_id), ('project_wbs_state', '=', 'approved')]")
