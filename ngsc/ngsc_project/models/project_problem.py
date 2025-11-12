from odoo import models, fields, api


class EnProblem(models.Model):
    _inherit = "en.problem"

    en_creator_id = fields.Many2one(string="Người ghi nhận")
    en_create_date = fields.Datetime(string="Ngày ghi nhận")