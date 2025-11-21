from odoo import models, fields, api, _, exceptions
from odoo.exceptions import UserError, ValidationError
import json


class CrmStage(models.Model):
    _inherit = 'crm.stage'

    probability = fields.Float(string='Xác xuất', default=0, compute='_compute_probabilities', readonly=False, store=True)

    @api.depends('is_won')
    def _compute_probabilities(self):
        for rec in self:
            probability = rec.probability
            if rec.is_won: probability = 100
            rec.probability = probability

    x_required_field_ids = fields.Many2many(string='Thông tin bắt buộc', comodel_name='ir.model.fields', domain="[('model','=','crm.lead')]")
    x_type = fields.Selection(selection=[('new', 'Tạo mới'), ('offer', 'Đề xuất'), ('estimates', 'Dự toán'), ('bidding', 'Đấu thầu'), ('close', 'Thắng thua')], string="Loại")
    company_id = fields.Many2one('res.company', string="Công ty", default=lambda self: self.env.company)
    is_lost = fields.Boolean('Là giai đoạn thua?')