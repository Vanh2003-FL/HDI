from odoo import models, fields, api, _


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    maximum_workload = fields.Integer(string="% Workload tối đa của nhân sự", config_parameter="maximum_workload", default=100)
