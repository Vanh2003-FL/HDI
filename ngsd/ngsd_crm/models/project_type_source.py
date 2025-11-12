from odoo import api, fields, models, Command, _
from odoo.exceptions import UserError, ValidationError
import json


# class ProjectTypeSource(models.Model):
#     _name = 'project.type.source'
#     _description = "Loại hình cung cấp dự án"
#
#     name = fields.Char(string="Loại hình", required=True)
