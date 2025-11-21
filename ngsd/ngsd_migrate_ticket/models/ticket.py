from odoo import models, fields, api
import json
from lxml import etree


class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    en_day_rep = fields.Datetime(readonly=False)
    en_day_com = fields.Datetime(readonly=False)
    en_date_end = fields.Datetime(readonly=False)

    create_date_migrate = fields.Datetime('Ngày tiếp nhận')
    create_uid_migrate = fields.Many2one('res.users', string='Người yêu cầu - không sd')
    en_code = fields.Char(readonly=False)

    @api.model_create_multi
    def create(self, list_value):
        res = super().create(list_value)
        for rec in res:
            rec.create_date = rec.create_date_migrate
            rec.create_uid = rec.create_uid_migrate
        return res

    def write(self, values):
        if values.get('create_date_migrate'):
            values['create_date'] = values.get('create_date_migrate')
        if values.get('create_uid_migrate'):
            values['create_uid'] = values.get('create_uid_migrate')
        res = super().write(values)
        return res
