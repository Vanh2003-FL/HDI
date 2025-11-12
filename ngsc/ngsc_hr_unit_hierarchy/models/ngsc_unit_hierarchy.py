# -*- coding: utf-8 -*-
from odoo import models, fields, api
from ..utils.query import *


class NgscUnitHierarchy(models.Model):
    _name = "ngsc.unit.hierarchy"
    _order = "name asc"
    _description = "Phân cấp phòng ban/trung tâm/khối/khu vực"

    name = fields.Char(string="Tên đơn vị")
    parent_id = fields.Many2one("ngsc.unit.hierarchy", string="Đơn vị cha")
    active = fields.Boolean(string="Hoạt động", default=True)
    unit_type = fields.Selection(string="Loại",
                                 selection=[('area', 'Khu vực'),
                                            ('block', 'Khối'),
                                            ('department', 'Trung tâm/Ban'),
                                            ('en_department', 'Phòng')])
    block_id = fields.Many2one("en.name.block", string="Khối")
    department_id = fields.Many2one("hr.department", string="Trung tâm/Ban", index=True)
    en_department_id = fields.Many2one("en.department", string="Phòng", index=True)