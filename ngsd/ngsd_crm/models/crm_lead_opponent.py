from odoo import models, fields, api, _, exceptions
from odoo.exceptions import UserError, ValidationError


class CrmLeadOpponent(models.Model):
    _name = 'crm.lead.opponent'
    _description = 'Crm Lead Opponent'

    lead_id = fields.Many2one(
        comodel_name='crm.lead',
        required=True,
        ondelete='cascade',
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Đối thủ',
        domain="[('is_competitors', '=', True)]"
    )
    partner_text = fields.Text(
        string='Đối thủ',
    )
    solution = fields.Text(
        string='Giải pháp đề xuất',
    )
    price = fields.Float(
        string='Giá đề xuất', default=0
    )
    support_pid = fields.Many2one(
        comodel_name='res.partner',
        string='Đầu mối phía KH',
        domain="[('parent_id', '=', partner_id)]",
    )
    note = fields.Text(
        string='Ghi chú',
    )
    support_state_id = fields.Many2one(
        comodel_name='crm.support.state',
        string='Tình trạng hỗ trợ từ phía KH',
    )

