# -*- coding: utf-8 -*-
import logging

from odoo import api, SUPERUSER_ID
from . import models, report

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Auto-run migration after module update"""
    env = api.Environment(cr, SUPERUSER_ID, {})

    _logger.info("=== Starting auto-migration after module update ===")

    # Chạy migration cho project.task
    try:
        task_model = env['project.task']
        if hasattr(task_model, 'update_module_migration'):
            success = task_model.update_module_migration()
            if success:
                _logger.info("✅ Project Task migration completed successfully")
            else:
                _logger.error("❌ Project Task migration failed")
    except Exception as e:
        _logger.error(f"❌ Project Task migration error: {e}")

    # Chạy migration cho en.wbs
    try:
        wbs_model = env['en.wbs']
        if hasattr(wbs_model, 'update_module_migration'):
            success = wbs_model.update_module_migration()
            if success:
                _logger.info("✅ WBS migration completed successfully")
            else:
                _logger.error("❌ WBS migration failed")
    except Exception as e:
        _logger.error(f"❌ WBS migration error: {e}")

    _logger.info("=== Auto-migration finished ===")
