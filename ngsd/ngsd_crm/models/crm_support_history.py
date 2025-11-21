from odoo import api, fields, models, Command, _
from odoo.exceptions import UserError, ValidationError


class CRMSupportHistory(models.Model):
    _name = 'crm.support.history'
    _description = 'CRM Support History'

    x_date = fields.Date(required=True, string='Ngày')
    technical_field_27310 = fields.Many2many(string='🪙', compute='_compute_technical_field_27310', comodel_name='res.partner')

    @api.depends('x_lead_id.partner_id', 'x_lead_id.line_ids.supplier_id', 'x_lead_id.line_ids.partner_id')
    def _compute_technical_field_27310(self):
        for rec in self:
            rec.technical_field_27310 = self.env['res.partner'].search([('id', 'in', (rec.x_lead_id.partner_id | rec.x_lead_id.line_ids.mapped('supplier_id') | rec.x_lead_id.line_ids.mapped('partner_id')).ids)])

    user_id = fields.Many2one(related='x_lead_id.user_id', store=True)
    x_partner_id = fields.Many2one('res.partner', string='Đối tượng')
    partner_id = fields.Many2one(related='x_lead_id.partner_id', store=True, readonly=False)
    x_description = fields.Text(string='Ghi chú')
    x_note = fields.Text(required=True, string='Nội dung')
    x_lead_id = fields.Many2one('crm.lead', required=False, string='Cơ hội')
    x_is_sale = fields.Boolean(compute='_compute_x_is_sale', store=True)

    @api.depends('x_partner_id')
    def _compute_x_is_sale(self):
        for rec in self:
            rec.x_is_sale = self.env.user in rec.x_partner_id.user_ids
