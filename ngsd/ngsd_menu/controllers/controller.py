from odoo import http, models
from odoo.addons.website_blog.controllers.main import WebsiteBlog
from odoo.addons.website.controllers.main import Website
from odoo.http import request


class BlogController(WebsiteBlog):
    @http.route(auth="user")
    def blog(self, blog=None, tag=None, page=1, search=None, **opt):
        return super(BlogController, self).blog(blog=blog, tag=tag, page=page, search=search, **opt)

class InheritWebsite(Website):
    @http.route(auth="user")
    def index(self, **kw):
        return super(InheritWebsite, self).index(**kw)

class HttpInherit(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _serve_page(cls):
        if http.request.env.user.id == http.request.website.user_id.id:
            return request.redirect('/web/login')
        return super()._serve_page()
