from odoo import models, fields, api, _


class EnProjectLevel(models.Model):
    _name = "en.project.level"
    _description = "Cấp độ dự án"

    name = fields.Char(string="Cấp độ dự án", required=True)
    description = fields.Text(string="Mô tả")