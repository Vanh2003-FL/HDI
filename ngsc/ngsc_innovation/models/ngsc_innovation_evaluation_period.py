# -*- coding: utf-8 -*-
from odoo import models, fields, api, _, exceptions
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta


class NgscInnovationEvaluationPeriod(models.Model):
    _name = 'ngsc.innovation.evaluation.period'
    _description = 'Thiết lập thời gian chấm điểm'

    name = fields.Char(
        string='Tên',
        default='Thiết lập thời gian chấm điểm',
        required=True
    )

    start_date = fields.Date(
        string='Ngày bắt đầu chấm điểm',
        required=True,
        help='Ngày thành viên trong hội đồng đánh giá có thể thực hiện chấm điểm'
    )

    end_date = fields.Date(
        string='Ngày kết thúc chấm điểm',
        required=True,
        help='Ngày thành viên trong hội đồng đánh giá có thể thực hiện chấm điểm'
    )

    reminder_days = fields.Integer(
        string='Thời gian gửi Email thông báo cho đơn đánh giá',
        help='Thời gian gửi Email thông báo trước ngày kết thúc chấm điểm',
        default=48
    )

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for record in self:
            if record.start_date and record.end_date:
                if record.start_date > record.end_date:
                    raise ValidationError(_('Ngày bắt đầu phải trước ngày kết thúc'))

    @api.model
    def is_evaluation_period(self):
        today = fields.Date.today()
        current_period = self.search([
            ('start_date', '<=', today),
            ('end_date', '>=', today)
        ], limit=1)
        return bool(current_period)