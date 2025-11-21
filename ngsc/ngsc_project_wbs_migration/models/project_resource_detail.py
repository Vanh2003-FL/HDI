from datetime import timedelta, datetime
import logging
from odoo import models, fields, api, _
from setuptools.dist import sequence

_logger = logging.getLogger(__name__)


class ResourceDetail(models.Model):
    _inherit = "en.resource.detail"

    @api.constrains('date_start', 'date_end', 'employee_id', 'workload')
    def check_workload_borrow(self):
        if self._context.get("migration_data", False):
            return
        super().check_workload_borrow()

    @api.constrains("project_task_stage_id", "date_start", "date_end")
    def _check_date_start_and_end(self):
        if self._context.get("migration_data", False):
            return
        super()._check_date_start_and_end()
