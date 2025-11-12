# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo import http
from odoo.http import request


class ViewApproval(http.Controller):

    @http.route(['/web_view_action/<string:model>/<int:id>'], type='http', auth="user")
    def web_view_action(self, model, id):
        record = request.env[model].browse(id)
        new_url = f'/web#model={model}&id={id}&view_type=form'
        if hasattr(record, 'get_action_view_from_id'):
            action = getattr(record, 'get_action_view_from_id')()
            if action:
                new_url += '&action=' + str(action.id)
        return request.redirect(new_url)
