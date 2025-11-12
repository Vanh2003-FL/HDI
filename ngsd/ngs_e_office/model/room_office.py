# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class RoomOffice(models.Model):
    _name = "room.office"
    _description = "Văn phòng"
    _order = "name, id"

    name = fields.Char(string="Tên văn phòng", required=True, translate=True)
    company_id = fields.Many2one("res.company", string="Công ty", default=lambda self: self.env.company, required=True)
    active = fields.Boolean('Hoạt động', default=True)

    def name_get(self):
        return [(record.id, f"{record.name} - {record.company_id.name}") for record in self]
