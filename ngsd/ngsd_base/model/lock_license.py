# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, tools


class LockLicense(models.Model):
    _description = 'Lock license'
    _name = 'lock.license'
    _order = 'id DESC'

    date_lock = fields.Datetime("Ngày khóa chúng từ", required=1)
    state = fields.Selection(selection=[('new', 'Mới'), ('locked', 'Đã khóa sổ')], string='Trạng thái', default='new',  required=1)
    type = fields.Selection(selection=[('create', 'Khai Timesheet'), ('approve', 'Duyệt Timesheet')], string='Loại khoá sổ', required=1)

    def action_lock(self):
        key = 'lock_' + self.type + '_timesheet'
        if hasattr(self.env['hr.employee'], key):
            self.env.cr.execute(f"UPDATE hr_employee SET {key} = '{self.date_lock.strftime('%Y-%m-%d %H:%M:%S')}' WHERE {key + '_exp'} is null or {key + '_exp'} < '{fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')}'")
        self.sudo().write({'state': 'locked'})

    def action_change_date_expire(self):
        for type_lock in ['create', 'approve']:
            date_lock = self.get_lasted_date_lock(type_lock)
            key = 'lock_' + type_lock + '_timesheet'
            if date_lock and hasattr(self.env['hr.employee'], key):
                self.env.cr.execute(f"UPDATE hr_employee SET {key} = '{date_lock.strftime('%Y-%m-%d %H:%M:%S')}' WHERE {key + '_exp'} is null or {key + '_exp'} < '{fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')}'")

    def get_lasted_date_lock(self, type):
        return self.env['lock.license'].search([('type', '=', type), ('state', '=', 'locked')], limit=1, order='id DESC').date_lock

    def action_auto_lock(self):
        date_lock = fields.Datetime.now() - relativedelta(days=1)
        create_license = self.create({
            'date_lock': date_lock,
            'type': 'create'
        })
        create_license.action_lock()
        approve_license = self.create({
            'date_lock': date_lock,
            'type': 'approve'
        })
        approve_license.action_lock()
