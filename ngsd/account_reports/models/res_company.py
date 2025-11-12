from odoo import models, fields
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT

from datetime import timedelta, datetime
from odoo.tools import date_utils

class ResCompany(models.Model):
    _inherit = 'res.company'

    def compute_fiscalyear_dates(self, current_date):
        self.ensure_one()
        date_from, date_to = date_utils.get_fiscal_year(current_date, day=31, month=int(12))
        return {'date_from': date_from, 'date_to': date_to}
