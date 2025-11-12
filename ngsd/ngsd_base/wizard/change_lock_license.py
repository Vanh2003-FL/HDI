from odoo import models, api, fields, _, exceptions

from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)


class ChangeLockLicense(models.Model):
    _name = 'change.lock.license'
    _description = 'Change Lock License'

    employee_ids = fields.Many2many('hr.employee', string='Nhân viên', required=1)
    date_lock = fields.Datetime("Ngày khóa chúng từ", required=1, default=fields.Datetime.now)
    date_expire = fields.Datetime("Hiệu lực đến", required=1)
    type = fields.Char(required=1)

    def button_confirm(self):
        key = 'lock_' + self.type + '_timesheet'
        if hasattr(self.env['hr.employee'], key):
            self.env.cr.execute(f"UPDATE hr_employee SET {key} = %s, {key + '_exp'} = %s WHERE id IN %s", (self.date_lock, self.date_expire, tuple(self.employee_ids.ids),))
