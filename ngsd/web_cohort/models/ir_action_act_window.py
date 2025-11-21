# -*- coding: utf-8 -*-
from odoo import models, fields, _


class ActWindowView(models.Model):
    _inherit = 'ir.actions.act_window.view'

    view_mode = fields.Selection(selection_add=[
        ('cohort', 'Cohort')
    ], ondelete={'cohort': 'cascade'})
