# -*- coding: utf-8 -*-
from odoo import models, fields, api


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    contract_type_id = fields.Many2one("hr.contract.type", string="Loại hợp đồng",
                                       related="contract_id.contract_type_id", related_sudo=True, store=True)
