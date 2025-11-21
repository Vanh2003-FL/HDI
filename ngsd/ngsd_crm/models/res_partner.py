from odoo import models, fields, api, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    en_gender = fields.Selection(string='Giới tính', selection=[('male', 'Nam'), ('female', 'Nữ'), ('other', 'Khác')])
    x_count_contract = fields.Integer(string='Hợp đồng', compute='_compute_x_count_contract', compute_sudo=True)

    def name_get(self):
        return super(ResPartner, self.sudo()).name_get()

    @api.depends()
    def _compute_x_count_contract(self):
        for rec in self:
            rec.x_count_contract = self.env['x.sale.contract'].search_count([('partner_id', '=', rec._origin.id)]) if rec._origin.id else 0

    def to_x_count_contract(self):
        return self.open_form_or_tree_view(action='ngsd_crm.action_sale_contract', records=self.env['x.sale.contract'].search([('partner_id', 'in', self.ids)]))

    x_support_history_ids = fields.One2many('crm.support.history', 'partner_id', string='Lịch sử chăm sóc', domain=[('x_lead_id', '=', False)])
