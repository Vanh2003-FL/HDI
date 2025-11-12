import json
import traceback

from werkzeug.urls import url_encode, url_join

from odoo import exceptions, registry
from odoo.http import request

from odoo.addons.base_rest.http import JSONEncoder
from odoo.addons.component.core import AbstractComponent


class BaseRESTService(AbstractComponent):
    _inherit = "base.rest.service"

    def _log_call_in_db(self, env, _request, method_name, *args, params=None, **kw):
        super()._log_call_in_db(env, _request, method_name, *args, params, **kw)
        return

    def _get_log_entry_url(self, entry):
        return ""
