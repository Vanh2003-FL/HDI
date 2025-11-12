
from odoo import http, tools
from odoo.addons.web_editor.controllers.main import Web_Editor

class Web_EditorNGS(Web_Editor):

    @http.route("/web_editor/ensure_common_history", type="json", auth="user")
    def ensure_common_history(self, model_name, field_name, res_id, history_ids):
        return
