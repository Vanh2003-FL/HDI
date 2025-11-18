# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class HrLeave(models.Model):
    _inherit = 'hr.leave'
    
    # HDI Leave Extensions
    hdi_leave_code = fields.Char(
        string='Mã đơn nghỉ phép HDI',
        readonly=True,
        copy=False
    )
    
    hdi_replacement_employee_id = fields.Many2one(
        'hr.employee',
        string='Người thay thế',
        help='Nhân viên thay thế trong thời gian nghỉ phép'
    )
    
    hdi_handover_status = fields.Selection([
        ('none', 'Không cần bàn giao'),
        ('pending', 'Chờ bàn giao'),
        ('completed', 'Đã bàn giao'),
    ], string='Trạng thái bàn giao', default='none')
    
    hdi_handover_note = fields.Text(
        string='Ghi chú bàn giao công việc'
    )
    
    hdi_urgent_contact = fields.Char(
        string='Liên hệ khẩn cấp',
        help='Số điện thoại liên hệ khẩn cấp khi nghỉ phép'
    )

    @api.model
    def create(self, vals):
        # Auto generate HDI leave code
        if not vals.get('hdi_leave_code'):
            vals['hdi_leave_code'] = self.env['ir.sequence'].next_by_code('hdi.leave') or 'HDI/LV/0001'
        return super().create(vals)


class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'
    
    # HDI Leave Type Extensions
    hdi_requires_handover = fields.Boolean(
        string='Yêu cầu bàn giao',
        default=False,
        help='Loại nghỉ phép này có yêu cầu bàn giao công việc không'
    )
    
    hdi_min_advance_days = fields.Integer(
        string='Số ngày báo trước tối thiểu',
        default=1,
        help='Số ngày tối thiểu phải báo trước khi nghỉ phép'
    )
    
    hdi_max_consecutive_days = fields.Integer(
        string='Số ngày nghỉ liên tục tối đa',
        help='Số ngày nghỉ liên tục tối đa cho loại nghỉ phép này'
    )


class HrLeaveAllocation(models.Model):
    _inherit = 'hr.leave.allocation'
    
    # HDI Leave Allocation Extensions
    hdi_allocation_code = fields.Char(
        string='Mã phân bổ nghỉ phép HDI',
        readonly=True,
        copy=False
    )
    
    hdi_carry_forward = fields.Boolean(
        string='Được chuyển sang năm sau',
        default=False,
        help='Số ngày phép này có được chuyển sang năm sau không'
    )
    
    hdi_expire_date = fields.Date(
        string='Ngày hết hạn',
        help='Ngày hết hạn sử dụng số ngày phép này'
    )

    @api.model
    def create(self, vals):
        # Auto generate HDI allocation code
        if not vals.get('hdi_allocation_code'):
            vals['hdi_allocation_code'] = self.env['ir.sequence'].next_by_code('hdi.leave.allocation') or 'HDI/AL/0001'
        return super().create(vals)