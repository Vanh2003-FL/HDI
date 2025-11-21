from odoo import models, fields, _


class EnProcessingRateSnapshot(models.Model):
    _name = 'en.processing.rate.snapshot'
    _description = 'Cam kết tỷ lệ xử lý snapshot'

    project_decision_id = fields.Many2one('project.decision', string='QĐ TL Dự án', ondelete='cascade')
    start_date = fields.Date('Từ ngày')
    end_date = fields.Date('Đến ngày')
    rate = fields.Float('Tỷ lệ %')