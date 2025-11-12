# -*- coding: utf-8 -*-

from odoo import api, fields, models


class CrmLeadWin(models.TransientModel):
    _name = 'crm.lead.win'
    _description = 'Get Win Contract data'

    contract_code = fields.Char(string='Số hợp đồng')
    date_deadline = fields.Date('Ngày ký hợp đồng')

    def action_win_apply(self):
        leads = self.env['crm.lead'].browse(self.env.context.get('active_ids'))
        leads.write({'contract_code': self.contract_code, 'date_deadline': self.date_deadline})
        return leads.action_set_won_rainbowman()
