# Copyright 2018 ACSONE SA/NV
# Copyright 2017 Akretion (http://www.akretion.com).
# @author Sébastien BEAU <sebastien.beau@akretion.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import logging

from odoo import models
from odoo.exceptions import AccessDenied
from odoo.http import request

_logger = logging.getLogger(__name__)


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _auth_method_basic_auth(cls):
        headers = request.httprequest.environ
        auth_key = headers.get('HTTP_AUTHORIZATION')
        if auth_key == 'Basic cG93ZXJiaTpwb3dlcmJp':
            # reset _env on the request since we change the uid...
            # the next call to env will instantiate an new
            # odoo.api.Environment with the user defined on the
            # auth.api_key
            request._env = None
            request.uid = 2
            return True
        _logger.error("Wrong HTTP_API_KEY, access denied")
        raise AccessDenied()
