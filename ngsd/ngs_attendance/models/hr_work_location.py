from odoo import models, fields, api, _, exceptions


class WorkLocation(models.Model):
    _inherit = 'hr.work.location'

    en_latitude = fields.Float('Vĩ độ', digits=(10, 7))
    en_longitude = fields.Float('Kinh độ', digits=(10, 7))
    address_id = fields.Many2one(required=False)

    def pre_button_done(self, latitude, longitude):
        self.en_latitude = latitude
        self.en_longitude = longitude
