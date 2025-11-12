from odoo import models, fields


class ReportDataHumanResource(models.Model):
    _name = "report.data.human"
    _description = "Báo cáo mẫu"

    name = fields.Char(string='tên', required=True)