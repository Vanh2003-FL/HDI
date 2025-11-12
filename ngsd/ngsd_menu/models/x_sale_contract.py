from odoo import models, fields, api, _, exceptions
import datetime
from odoo.exceptions import UserError


class Contract(models.Model):
    _inherit = 'x.sale.contract'

    en_sales_sp_id = fields.Many2one(domain=lambda self: [('id', 'in', self.env.ref('ngsd_menu.group_sale_salesman_support_leads').users.ids)])
