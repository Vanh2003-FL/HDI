# -*- coding: utf-8 -*-
from odoo import fields, models, api, Command, exceptions, _
from datetime import date, datetime
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta
from odoo.tools.float_utils import float_round


class HrAttendanceExplanationDetail(models.Model):
    """Chi tiết giải trình - cho phép điều chỉnh check in/out time"""
    _name = 'hr.attendance.explanation.detail'
    _description = 'Chi tiết giải trình chấm công'
    _order = 'sequence, id'

    explanation_id = fields.Many2one(
        'hr.attendance.explanation',
        string='Giải trình chấm công',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    sequence = fields.Integer(string='Thứ tự', default=10)
    
    type = fields.Selection(
        [('check_in', 'Check In'), ('check_out', 'Check Out')],
        string='Loại điều chỉnh',
        required=True
    )
    
    time = fields.Float(
        string='Thời gian thực tế',
        required=True,
        help='Nhập giờ dạng 24h (VD: 8.5 = 8h30, 17.25 = 17h15)'
    )
    
    date = fields.Datetime(
        string='Giá trị mới',
        compute='_compute_date',
        store=True,
        readonly=False
    )
    
    @api.depends('time', 'explanation_id.explanation_date')
    def _compute_date(self):
        """Tính toán datetime từ date + time"""
        for rec in self:
            if rec.explanation_id.explanation_date and rec.time:
                rec.date = rec.explanation_id.explanation_date + rec._float_to_relativedelta(rec.time) - relativedelta(hours=7)
            else:
                rec.date = False
    
    def _float_to_relativedelta(self, float_hour):
        """Convert float hour to relativedelta"""
        if float_hour >= 24:
            float_hour = 23.9999
        minute = (float_hour % 1) * 60
        second = (minute % 1) * 60
        return relativedelta(
            hour=int(float_hour),
            minute=int(minute),
            second=int(second),
            microsecond=0
        )
    
    @api.constrains('explanation_id', 'type')
    def _check_duplicate_type(self):
        """Đảm bảo mỗi loại chỉ có 1 dòng"""
        for rec in self:
            count = self.search_count([
                ('explanation_id', '=', rec.explanation_id.id),
                ('type', '=', rec.type)
            ])
            if count > 1:
                raise ValidationError(_('Chỉ có thể chọn 1 giá trị %s') % dict(self._fields['type'].selection)[rec.type])
    
    @api.constrains('time')
    def _check_valid_time(self):
        """Validate time trong khoảng 00:00-23:59"""
        for rec in self:
            if not (0.01 <= rec.time <= 23.99):
                raise ValidationError(_('Giá trị thời gian không hợp lệ (00:01-23:59)'))
