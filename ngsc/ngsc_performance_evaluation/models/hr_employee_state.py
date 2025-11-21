# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class HrPerformanceEvaluation(models.Model):
    _name = "hr.employee.state"
    _description = "Tình trạng nhân sự"

    code = fields.Char(string="Mã", required=True, unique=True)
    name = fields.Char(string="Tình trạng", required=True, unique=True)
