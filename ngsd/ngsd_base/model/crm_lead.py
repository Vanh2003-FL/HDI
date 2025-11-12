from odoo import *


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    en_project = fields.Many2one(string='Dự án', comodel_name='project.project')
