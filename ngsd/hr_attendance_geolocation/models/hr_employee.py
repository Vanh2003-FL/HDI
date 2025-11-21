# Copyright 2019 ForgeFlow S.L.
# Copyright 2023 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, _
from geopy.geocoders import Nominatim

from logging import getLogger
_logger = getLogger(__name__)


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    def _attendance_action_change(self):
        res = super()._attendance_action_change()
        latitude = self.env.context.get("latitude", False)
        longitude = self.env.context.get("longitude", False)
        if latitude and longitude:
            try:
                geolocator = Nominatim(user_agent='my-app')
                location = geolocator.reverse(str(latitude) + ', ' + str(longitude))
            except Exception as e:
                _logger.warning("Error getting location: %s", e)
                location = False
            if self.attendance_state == "checked_in":
                res.sudo().write(
                    {
                        "check_in_latitude": latitude,
                        "check_in_longitude": longitude,
                        "check_in_address": location
                    }
                )
            else:
                res.sudo().write(
                    {
                        "check_out_latitude": latitude,
                        "check_out_longitude": longitude,
                        "check_out_address": location
                    }
                )
        return res
