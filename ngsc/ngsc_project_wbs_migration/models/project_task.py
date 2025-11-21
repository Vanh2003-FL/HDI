import logging
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class ProjectTask(models.Model):
    _inherit = "project.task"

    @api.constrains("en_start_date", "date_deadline")
    def _constrains_date(self):
        if self._context.get("migration_data", False):
            return
        super()._constrains_date()

    @api.constrains("stage_id")
    def _constrains_stage_in_progress(self):
        if self._context.get("migration_data", False):
            return
        super()._constrains_stage_in_progress()

    @api.constrains("stage_id")
    def _constrains_stage_task_complete(self):
        if self._context.get("migration_data", False):
            return
        super()._constrains_stage_task_complete()
