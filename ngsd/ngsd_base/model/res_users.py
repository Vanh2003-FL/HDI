from odoo import api, fields, models
from odoo.addons.account.models.res_users import GroupsView
from odoo.osv import expression


@api.model
def new_get_application_groups(self, domain):
    # Overridden in order to remove 'Show Full Accounting Features' and
    # 'Show Full Accounting Features - Readonly' in the 'res.users' form view to prevent confusion
    group_account_user = self.env.ref('account.group_account_user', raise_if_not_found=False)
    if group_account_user and group_account_user.category_id.xml_id == 'base.module_category_hidden':
        domain += [('id', '!=', group_account_user.id)]
    # group_account_readonly = self.env.ref('account.group_account_readonly', raise_if_not_found=False)
    # if group_account_readonly and group_account_readonly.category_id.xml_id == 'base.module_category_hidden':
    #     domain += [('id', '!=', group_account_readonly.id)]
    return self.search(domain + [('share', '=', False)])


GroupsView.get_application_groups = new_get_application_groups


class ResUsers(models.Model):
    _inherit = "res.users"

    technical_field_28159 = fields.Many2many(string='🐧', comodel_name='hr.employee', compute='_compute_technical_field_28159')

    @api.depends('employee_id')
    def _compute_technical_field_28159(self):
        for rec in self:
            rec.technical_field_28159 = self.env['project.project'].search([('en_project_qa_id', '=', rec.id)]).en_resource_id.order_line.mapped('employee_id')

    notification_type = fields.Selection(default='inbox')

    def action_create_employee(self):
        self.ensure_one()
        vals = dict(
            name=self.name,
            work_email=self.email,
            company_id=self.env.company.id,
            **self.env['hr.employee']._sync_user(self)
        )
        ctx = {}
        for key in vals:
            ctx[f'default_{key}'] = vals.get(key)
        return self.open_form_or_tree_view(action='hr.open_view_employee_list_my', context=ctx, action_name='Tạo nhân viên mới', target='new')

    from_groups_with_love = fields.One2many(string='Nhóm quyền đại diện', comodel_name='res.groups', inverse_name='from_user_with_love', readonly=True)

    def should_we_make_group(self):
        for rec in self:
            vals = {
                'name': f'{rec.name} - {rec.login}',
                'from_user_with_love': rec.id,
                'category_id': self.env.ref('ngsd_base.user_ngsd_categ').id,
                'users': [(6, 0, rec.ids)]
            }
            if not rec.from_groups_with_love:
                self.env['res.groups'].sudo().create(vals)
            else:
                rec.from_groups_with_love.sudo().write(vals)

    def unlink(self):
        if self.from_groups_with_love:
            self.from_groups_with_love.unlink()
        return super().unlink()

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        res.should_we_make_group()
        return res

    def write(self, vals):
        res = super().write(vals)
        if 'name' in vals or 'login' in vals:
            self.should_we_make_group()
        return res

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        user_ids = []
        if operator not in expression.NEGATIVE_TERM_OPERATORS:
            if operator == 'ilike' and not (name or '').strip():
                domain = []
            else:
                domain = [('login', '=', name)]
            user_ids = self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)
        if not user_ids:
            user_ids = self._search(expression.AND([[('name', operator, name)], args]), limit=limit, access_rights_uid=name_get_uid)
        return user_ids


class ResGroups(models.Model):
    _inherit = 'res.groups'

    from_user_with_love = fields.Many2one(string='Tạo tự động từ user', domain=[('active', 'in', [True, False])], comodel_name='res.users', readonly=True, copy=False)
    from_user_is_active = fields.Boolean(string='🪙', related='from_user_with_love.active')
    from_role_with_love = fields.Many2one(string='Tạo tự động từ vai trò', comodel_name='en.role', readonly=True, copy=False)

    @api.model
    def get_application_groups(self, domain):
        user_ngsd_categ = self.env.ref('ngsd_base.user_ngsd_categ', raise_if_not_found=False)
        if user_ngsd_categ:
            domain += [('category_id', '!=', user_ngsd_categ.id)]
        return super().get_application_groups(domain)
