# -*- coding: utf-8 -*-
from odoo.addons.base.models.ir_http import IrHttp
from odoo.exceptions import UserError
from odoo import models, api, _
import logging

_logger = logging.getLogger(__name__)


class CustomHttp(IrHttp):
    _name = 'ir.http'
    _description = "HTTP Routing"

    @classmethod
    def _handle_exception(cls, exception):
        if isinstance(exception, UserError):
            _logger.error(f"Global UserError: {exception}")
            return "🚨 System Alert: " + str(exception)
        return super()._handle_exception(exception)
