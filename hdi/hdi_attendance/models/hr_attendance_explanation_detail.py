# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HrAttendanceExplanationDetail(models.Model):
    _name = 'hr.attendance.explanation.detail'
    _description = 'Chi tiết giải trình chấm công'
    _order = 'sequence, id'

    explanation_id = fields.Many2one(
        'hr.attendance.explanation',
        string='Giải trình chấm công',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(string='Thứ tự', default=10)
    type = fields.Selection([
        ('check_in', 'Check In'),
        ('check_out', 'Check Out')
    ], string='Cần điều chỉnh', required=True)
    time = fields.Float(
        string='Thời gian thực tế',
        required=True,
        help='Thời gian dạng float, ví dụ: 8.5 = 8h30'
    )
    date = fields.Datetime(
        string='Giá trị mới',
        compute='_compute_date',
        store=True,
        readonly=False
    )

    @api.depends('explanation_id.explanation_date', 'time')
    def _compute_date(self):
        """Compute datetime from date + time"""
        for rec in self:
            if rec.explanation_id.explanation_date and rec.time:
                # Convert float time to datetime
                from datetime import datetime, timedelta
                date = rec.explanation_id.explanation_date
                hours = int(rec.time)
                minutes = int((rec.time - hours) * 60)
                rec.date = datetime.combine(date, datetime.min.time()) + timedelta(hours=hours, minutes=minutes)
            else:
                rec.date = False

    @api.constrains('explanation_id', 'type')
    def _constrains_order_n_type(self):
        """Ensure only one record per type"""
        for rec in self:
            if self.search_count([
                ('explanation_id', '=', rec.explanation_id.id),
                ('type', '=', rec.type),
                ('id', '!=', rec.id)
            ]) > 0:
                raise ValidationError(_('Chỉ được có một bản ghi %s cho mỗi giải trình.') % dict(self._fields['type'].selection)[rec.type])

    @api.constrains('time')
    def check_valid_hour(self):
        """Validate time is between 0 and 24"""
        for rec in self:
            if not (0 <= rec.time < 24):
                raise ValidationError(_('Thời gian phải nằm trong khoảng 0-24 giờ.'))
