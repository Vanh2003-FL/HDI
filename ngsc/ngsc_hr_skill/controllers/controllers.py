# -*- coding: utf-8 -*-
# from odoo import http


# class NgscConstance(http.Controller):
#     @http.route('/ngsc_utils/ngsc_utils', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/ngsc_utils/ngsc_utils/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('ngsc_utils.listing', {
#             'root': '/ngsc_utils/ngsc_utils',
#             'objects': http.request.env['ngsc_utils.ngsc_utils'].search([]),
#         })

#     @http.route('/ngsc_utils/ngsc_utils/objects/<model("ngsc_utils.ngsc_utils"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('ngsc_utils.object', {
#             'object': obj
#         })
