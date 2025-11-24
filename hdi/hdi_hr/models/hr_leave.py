# -*- coding: utf-8 -*-

from odoo import fields, models


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    hdi_leave_reason = fields.Text(string='Lý do nghỉ phép')
    hdi_backup_employee_id = fields.Many2one(
        'hr.employee',
        string='Người thay thế',
        help='Nhân viên thay thế trong thời gian nghỉ'
    )
