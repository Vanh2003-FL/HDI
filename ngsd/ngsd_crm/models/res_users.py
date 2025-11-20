from odoo import models, fields, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    x_consulting_team_id = fields.Many2one(string='Đội tư vấn', comodel_name='x.crm.consulting.team')
    x_development_team_id = fields.Many2one(string='Đội sản xuất', comodel_name='x.crm.development.team')
    team_my_lead_ids = fields.Many2many('crm.team', relation='crm_team_res_users_rel')
    user_my_lead_ids = fields.Many2many('res.users', relation='user_my_lead_rel', column1='lid', column2='mid', compute='_get_user_my_lead_ids', store=True)

    @api.depends('team_my_lead_ids')
    def _get_user_my_lead_ids(self):
        for rec in self:
            rec.user_my_lead_ids = rec.team_my_lead_ids.member_ids
