from odoo import api, models, _, exceptions, fields, SUPERUSER_ID
from odoo.fields import Domain
from odoo.addons.ngsd_entrust_dev_helper.tools.number2text import number2text_vn


class Base(models.AbstractModel):
    _inherit = "base"

    def convert_m2o_from_name(self, text):
        res = self.name_search(text, operator='=ilike')
        if res:
            return res[0][0]
        return False
