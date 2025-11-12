from odoo import models, fields, api


class EnProjectLegalEntity(models.Model):
    _name = "en.project.legal.entity"
    _description = "Pháp nhân ký HĐ"

    name = fields.Char(string="Pháp nhân ký HĐ", required=True)