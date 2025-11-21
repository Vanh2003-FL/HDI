from odoo import models, fields, api, _


class ProjectStage(models.Model):
    _inherit = "project.project.stage"


    def get_required_fields(self):
        return self.sudo().en_required_field_ids.mapped('name')
