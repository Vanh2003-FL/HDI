from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    maximum_workload = fields.Integer(string="% Workload tối đa của nhân sự", config_parameter="maximum_workload", default=100)
