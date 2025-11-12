from odoo.addons.base_rest.controllers import main


class NGSRestApiController(main.RestController):
    _root_path = "/api/"
    _collection_name = "all.rest.api.services"
    _default_auth = "basic_auth"

