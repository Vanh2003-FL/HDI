# -*- coding: utf-8 -*-
from odoo import http
from odoo.exceptions import UserError


class NgscConstance(http.Controller):
    @http.route('/ngsc/test', auth='public')
    def index(self, **kw):
        raise UserError("abcealfaleaf")
        # return "Hello, world"
