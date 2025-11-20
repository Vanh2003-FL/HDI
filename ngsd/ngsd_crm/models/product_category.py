from odoo import models, fields, api, _, exceptions
import json
import requests


class ProductCategory(models.Model):
    _inherit = "product.category"

    product_type_id = fields.Many2one('crm.product.type', string='Loại', required=True)
