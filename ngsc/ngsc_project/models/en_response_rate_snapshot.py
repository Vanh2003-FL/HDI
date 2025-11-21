from odoo import models, fields, _


class EnResponseRateSnapshot(models.Model):
    _name = 'en.response.rate.snapshot'
    _description = 'Cam kết tỷ lệ phản hồi snapshot'

    project_decision_id = fields.Many2one('project.decision', string='QĐ TL Dự án', ondelete='cascade')
    start_date = fields.Date('Từ ngày')
    end_date = fields.Date('Đến ngày')
    rate = fields.Float('Tỷ lệ %')