# -*- coding: utf-8 -*-
# from odoo import http


# class NgscConstance(http.Controller):
#     @http.route('/ngsc_constance/ngsc_constance', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/ngsc_constance/ngsc_constance/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('ngsc_constance.listing', {
#             'root': '/ngsc_constance/ngsc_constance',
#             'objects': http.request.env['ngsc_constance.ngsc_constance'].search([]),
#         })

#     @http.route('/ngsc_constance/ngsc_constance/objects/<model("ngsc_constance.ngsc_constance"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('ngsc_constance.object', {
#             'object': obj
#         })
