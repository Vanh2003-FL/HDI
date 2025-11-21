from odoo import models, fields, api, _, exceptions
from odoo.exceptions import UserError, ValidationError
import json
import datetime


class CrmLeadInvoice(models.Model):
    _name = 'x.crm.lead.invoice'
    _description = 'Kế hoạch doanh thu xuất hoá đơn'

    lead_id = fields.Many2one(string='Cơ hội', comodel_name='crm.lead', required=True, ondelete='restrict')
    date = fields.Date(string='Ngày hóa đơn', required=True)
    percent = fields.Float(string='Tỷ lệ', compute='_compute_percent', readonly=False, store=True, compute_sudo=True)

    @api.depends('lead_id.ngsd_revenue', 'amount')
    def _compute_percent(self):
        for rec in self:
            rec.percent = rec.amount / rec.lead_id.ngsd_revenue if rec.lead_id.ngsd_revenue else 0

    amount = fields.Float(string='Giá trị', compute='_compute_amount', readonly=False, store=True, compute_sudo=True)

    @api.depends('lead_id.ngsd_revenue', 'percent')
    def _compute_amount(self):
        for rec in self:
            rec.amount = rec.percent * rec.lead_id.ngsd_revenue

    note = fields.Text(string='Ghi chú')
    currency_id = fields.Many2one(string='Tiền tệ', related='lead_id.company_currency')


class CrmLeadPayment(models.Model):
    _name = 'x.crm.lead.payment'
    _description = 'Kế hoạch dòng tiền'

    lead_id = fields.Many2one(string='Cơ hội', comodel_name='crm.lead', required=True, ondelete='restrict')
    date = fields.Date(string='Ngày thanh toán', required=True)
    percent = fields.Float(string='Tỷ lệ', compute='_compute_percent', readonly=False, store=True, compute_sudo=True)

    @api.depends('lead_id.ngsd_revenue', 'amount')
    def _compute_percent(self):
        for rec in self:
            rec.percent = rec.amount / rec.lead_id.ngsd_revenue if rec.lead_id.ngsd_revenue else 0

    amount = fields.Float(string='Giá trị', compute='_compute_amount', readonly=False, store=True, compute_sudo=True)

    @api.depends('lead_id.ngsd_revenue', 'percent')
    def _compute_amount(self):
        for rec in self:
            rec.amount = rec.percent * rec.lead_id.ngsd_revenue

    note = fields.Text(string='Ghi chú')
    currency_id = fields.Many2one(string='Tiền tệ', related='lead_id.company_currency')


class CrmConsultingTeam(models.Model):
    _name = 'x.crm.consulting.team'
    _description = 'Đội tư vấn'

    name = fields.Char(string='Tên', required=True)
    user_ids = fields.Many2many(string='Trưởng nhóm', comodel_name='res.users')
    member_ids = fields.One2many(string='Thành viên', comodel_name='res.users', inverse_name='x_consulting_team_id')
    company_id = fields.Many2one(string='Công ty', comodel_name='res.company')


class CrmDevelopmentTeam(models.Model):
    _name = 'x.crm.development.team'
    _description = 'Đội sản xuất'

    name = fields.Char(string='Tên', required=True)
    user_ids = fields.Many2many(string='Trưởng nhóm', comodel_name='res.users')
    member_ids = fields.One2many(string='Thành viên', comodel_name='res.users', inverse_name='x_development_team_id')
    company_id = fields.Many2one(string='Công ty', comodel_name='res.company')


class Region(models.Model):
    _name = 'x.region'
    _description = 'Vùng miền'

    name = fields.Char(string='Vùng miền')


class CrmLead(models.Model):
    _inherit = 'crm.lead'
    _mail_post_access = 'read'

    en_short_name = fields.Char(related='partner_id.x_short', string='Tên viết tắt')

    x_am_lead_id = fields.Many2one(string='AM lead', comodel_name='res.users', compute='_compute_x_am_lead_id', store=True, readonly=False)
    x_am_lead_ids = fields.Many2many(
        string='AM lead',
        comodel_name='res.users',
        relation='crm_lead_x_am_lead_rel',  # Tên bảng trung gian riêng
        column1='crm_lead_id',  # Cột liên kết đến crm.lead
        column2='res_users_id',  # Cột liên kết đến res.users
        compute='_compute_x_am_lead_ids',
        store=True,
        readonly=False
    )

    @api.depends('team_id')
    def _compute_x_am_lead_id(self):
        for rec in self:
            x_am_lead_id = rec.x_am_lead_id
            if not x_am_lead_id and rec.team_id and rec.team_id.user_ids:
                x_am_lead_id = rec.team_id.user_ids[0]
            rec.x_am_lead_id = x_am_lead_id

    @api.depends('team_id')
    def _compute_x_am_lead_ids(self):
        for rec in self:
            if not rec.x_am_lead_ids and rec.team_id and rec.team_id.user_ids:
                rec.x_am_lead_ids = rec.team_id.user_ids[0]
            else:
                rec.x_am_lead_ids = rec.x_am_lead_ids or []

    x_region_id = fields.Many2one(string='Vùng miền', comodel_name='x.region')

    duplicate_lead_ids = fields.Many2many(compute_sudo=True)
    duplicate_lead_count = fields.Integer(compute_sudo=True)

    @api.constrains('x_lead_payment')
    def _constrains_lead_max_percent(self):
        if any(sum(rec.x_lead_payment.mapped('percent')) > 1 for rec in self):
            raise exceptions.ValidationError("Tổng tỷ lệ hóa đơn vượt quá 100%")

    payment_percent_leftover = fields.Float(string='🔧', compute='_compute_payment_percent_leftover', compute_sudo=True)

    @api.depends('x_lead_payment', 'x_lead_payment.percent')
    def _compute_payment_percent_leftover(self):
        for rec in self:
            rec.payment_percent_leftover = max(1 - sum(rec.x_lead_payment.mapped('percent')), 0)

    @api.constrains('x_lead_invoice')
    def _constrains_invoice_max_percent(self):
        if any(sum(rec.x_lead_invoice.mapped('percent')) > 1 for rec in self):
            raise exceptions.ValidationError("Tổng tỷ lệ thanh toán vượt quá 100%")

    invoice_percent_leftover = fields.Float(string='🔧', compute='_compute_invoice_percent_leftover', compute_sudo=True)

    @api.depends('x_lead_invoice', 'x_lead_invoice.percent')
    def _compute_invoice_percent_leftover(self):
        for rec in self:
            rec.invoice_percent_leftover = max(1 - sum(rec.x_lead_invoice.mapped('percent')), 0)

    x_internal_plan = fields.Char(string='Phương án kinh doanh nội bộ')
    x_into_plan = fields.Char(string='Phương án vào thầu')
    x_doing_plan = fields.Char(string='Phương án thực hiện hợp đồng sơ bộ')
    x_revenue_plan = fields.Char(string='Kế hoạch doanh thu dự kiến')
    x_detail_plan = fields.Char(string='Kế hoạch chi tiết đến lúc ra thầu')

    company_currency = fields.Many2one(readonly=False, required=True)

    @api.depends(lambda self: ['stage_id', 'team_id'] + self._pls_get_safe_fields())
    def _compute_probabilities(self):
        for rec in self:
            rec.probability = rec.stage_id.probability

    def create_x_contract(self):
        ctx = {
            'default_lead_id': self.id,
            'default_en_team_id': self.team_id.id,
            'default_date_sign': self.date_deadline,
            'default_currency_id': self.company_currency.id,
            'default_x_project_type_id': self.x_project_type_id.id,
            'default_x_payment_schedule_ids': [(0, 0, {'currency_id': line.currency_id.id, 'payment_date': line.date, 'x_percent': line.percent, 'note': line.note}) for line in self.x_lead_payment],
            'default_partner_id': self.partner_id.id,
            'default_user_id': self.env.user.id,
            'default_line_ids': [(0, 0, {'name': line.product_name, 'product_uom_qty': 1, 'price_unit': line.ngsd_revenue}) for line in self.line_ids],
        }
        return self.open_form_or_tree_view('ngsd_crm.action_sale_contract', False, False, ctx, 'Tạo hợp đồng', 'new')

    def to_x_contract(self):
        return self.open_form_or_tree_view('ngsd_crm.action_sale_contract', False, self.x_contract_ids, {'default_lead_id': self.id, 'create': False})

    x_contract_ids = fields.One2many(string='Hợp đồng', inverse_name='lead_id', comodel_name='x.sale.contract')
    x_contract_count = fields.Integer(string='Hợp đồng', compute='_compute_x_contract_count', compute_sudo=True)

    @api.depends('probability', 'automated_probability')
    def _compute_is_automated_probability(self):
        for lead in self:
            lead.is_automated_probability = False

    @api.depends('x_contract_ids')
    def _compute_x_contract_count(self):
        for rec in self:
            rec.x_contract_count = len(rec.x_contract_ids)

    @api.constrains('stage_id')
    def _constrains_required_by_stage(self):
        self = self.sudo()
        for rec in self:
            if not rec.stage_id.x_required_field_ids:
                continue
            missed_fields = []
            for req in rec.stage_id.x_required_field_ids:
                if not rec[req.name]:
                    missed_fields += [req.with_context(lang=self.env.user.lang).field_description]
            if missed_fields:
                raise ValidationError(f"Chưa điền các thông tin bắt buộc tại {', '.join(missed_fields)}")

    x_lead_invoice = fields.One2many(string='Kế hoạch doanh thu xuất hoá đơn', comodel_name='x.crm.lead.invoice', inverse_name='lead_id')
    x_lead_payment = fields.One2many(string='Kế hoạch dòng tiền', comodel_name='x.crm.lead.payment', inverse_name='lead_id')
    x_consulting_team = fields.Many2many(string='Đội tư vấn', comodel_name='x.crm.consulting.team', compute='_compute_x_consulting_team', store=True, readonly=False)

    @api.depends('solution_architect_uids')
    def _compute_x_consulting_team(self):
        for rec in self:
            x_consulting_team = rec.x_consulting_team
            x_consulting_team |= rec.solution_architect_uids.mapped('x_consulting_team_id')
            rec.x_consulting_team = x_consulting_team

    x_development_team = fields.Many2many(string='Đội sản xuất', comodel_name='x.crm.development.team')
    x_expected_ratio = fields.Float(string='Tỷ suất lợi nhuận (dự kiến)', compute='_compute_x_expected_margin', store=True)
    x_expected_margin = fields.Float(string='Lợi nhuận (dự kiến)', compute='_compute_x_expected_margin', store=True)

    @api.depends('line_ids.ngsd_revenue_taxed', 'ngsd_revenue')
    def _compute_x_expected_margin(self):
        for rec in self:
            x_expected_margin = sum(rec.line_ids.mapped('ngsd_revenue_taxed'))
            rec.x_expected_margin = x_expected_margin
            rec.x_expected_ratio = x_expected_margin / rec.ngsd_revenue if rec.ngsd_revenue else 0

    @api.depends('line_ids.product_name')
    def compute_product_names(self):
        for rec in self:
            if not rec.line_ids or rec.company_id.company_type != 'ngsd':
                rec.product_names = False
                continue
            rec.product_names = ', '.join(rec.line_ids.mapped('product_name'))

    kickoff_planned_date = fields.Date(
        string='Ngày kickoff (Khởi động/Triển khai) dự án',
    )
    ngsd_revenue = fields.Float(
        string='Giá trị hợp đồng NGSC (Bao gồm cả VAT)', compute='_get_ngsd_revenue', store=True
    )
    total_revenue = fields.Float(
        string='Doanh thu', compute='_get_total_revenue', store=True
    )

    ngsd_revenue_taxed = fields.Float(
        string='Lợi nhuận dự kiến NGSC', compute='_get_ngsd_revenue_taxed', store=True
    )

    gross_profit_ratio = fields.Float(string='Tỷ lệ lãi gộp', default=0)
    gross_profit_value = fields.Float(string='Giá trị lãi gộp', compute='_compute_gross_profit_value', store=True)
    legal_id = fields.Many2one('x.legal', string='Pháp Nhân')
    contract_code = fields.Char(string='Số hợp đồng')

    ncs_revenue = fields.Float(string='Doanh số', default=0)

    @api.depends('expected_revenue', 'gross_profit_ratio')
    def _compute_gross_profit_value(self):
        for record in self:
            if record.company_type == 'ncs':
                record.gross_profit_value = record.ncs_revenue * record.gross_profit_ratio
            else:
                record.gross_profit_value = record.expected_revenue * record.gross_profit_ratio

    @api.depends('line_ids', 'line_ids.ngsd_revenue')
    def _get_ngsd_revenue(self):
        for rec in self:
            rec.ngsd_revenue = sum(rec.line_ids.mapped('ngsd_revenue'))

    @api.depends('line_ids', 'line_ids.total_revenue')
    def _get_total_revenue(self):
        for rec in self:
            rec.total_revenue = sum(rec.line_ids.mapped('total_revenue'))

    @api.depends('line_ids', 'line_ids.ngsd_revenue_taxed')
    def _get_ngsd_revenue_taxed(self):
        for rec in self:
            rec.ngsd_revenue_taxed = sum(rec.line_ids.mapped('ngsd_revenue_taxed'))

    expected_revenue = fields.Float(
        compute='_get_expected_revenue', store=True
    )

    @api.depends('line_ids', 'line_ids.estimated_value')
    def _get_expected_revenue(self):
        for rec in self:
            rec.expected_revenue = sum(rec.line_ids.mapped('estimated_value'))

    solution_architect_uids = fields.Many2many(
        comodel_name='res.users',
        string='SA',
    )

    partner_id = fields.Many2one(domain="[('is_customer', '=', True)]")
    main_partner_id = fields.Many2one('res.partner', string="NCC chính", compute="_get_main_partner_id", compute_sudo=True)

    @api.depends('line_ids', 'line_ids.partner_id')
    def _get_main_partner_id(self):
        for rec in self:
            rec.main_partner_id = rec.line_ids[:1].partner_id

    tender_model_id = fields.Many2one(
        comodel_name='crm.tender.model',
        string='Mô hình vào thầu',
    )
    role_id = fields.Many2one(
        comodel_name='crm.role',
        string='Vai trò của NGS',
    )
    product_names = fields.Text(
        string='Sản phẩm',
        compute='compute_product_names',
        store=True,
    )
    line_ids = fields.One2many(
        comodel_name='crm.lead.line',
        inverse_name='lead_id',
    )
    contact_ids = fields.One2many(
        comodel_name='crm.lead.contact',
        inverse_name='lead_id',
    )
    opponent_ids = fields.One2many(
        comodel_name='crm.lead.opponent',
        inverse_name='lead_id',
    )

    priority = fields.Selection(selection_add=[('3'), ('4', 'Mức độ 4'), ('5', 'Mức độ 5')], tracking=True)

    ncs_state = fields.Selection(selection=[
        ('solution_consulting', 'Tư vấn giải pháp'),
        ('poc', 'PoC'),
        ('solution_choose', 'Lựa chọn giải pháp'),
        ('estimates', 'Viết thuyết minh và dự toán'),
        ('bidding', 'Đấu thầu'),
        ('iontract', 'Ký hợp đồng'),
        ('implementation', 'Triển khai'),
        ('acceptance_periods', 'Nghiệm thu các kỳ'),
        ('overall_acceptance', 'Nghiệm thu tổng thể, thanh lý'),
    ], tracking=True, string="Trạng thái hiện tại")

    code = fields.Char('Mã/ID Lead', readonly=True)

    def _compute_code(self):
        for rec in self:
            if rec.company_id.company_type == 'ngsd':
                rec.code = self.env['ir.sequence'].next_by_code('seq.code.lead')
            elif rec.company_id.company_type == 'ncs':
                rec.code = self.env['ir.sequence'].next_by_code('ngsd.base.crm.lead')
            else:
                rec.code = False

    # TODO: Migrate _sql_constraints to individual models.Constraint objects
    _sql_constraints = [('code_uniq', 'unique(code)', "Mã/ID Lead đã tồn tại!")]

    x_support_history_ids = fields.One2many('crm.support.history', 'x_lead_id', string='Lịch sử chăm sóc')
    # cheat: đặt thêm field lên view
    x_process_history_ids = fields.One2many('crm.support.history', related="x_support_history_ids", string='Mô tả chi tiết tiến độ', readonly=False)

    x_support_history_ids_no_ngsd = fields.One2many('crm.support.history', related='x_support_history_ids', readonly=False)
    budget_approval_date = fields.Date('Ngày duyệt dự án ngân sách')
    bid_opening_date = fields.Date('Ngày mở thầu')
    bid_closing_date = fields.Date('Ngày đóng thầu')
    project_end_date = fields.Date('Ngày kết thúc dự án')
    to_sign_date = fields.Date('Dự kiến ký hợp đồng')
    to_sign_xhd = fields.Date('Dự kiến XHD')
    x_ktv_ids = fields.Many2many('kt.department', string="Phòng kỹ thuật")
    x_project_type_id = fields.Many2one('project.type.source', string="Loại hợp đồng")

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super(CrmLead, self).fields_get(allfields, attributes=attributes)
        if 'solution_architect_uids' in res:
            users = self.env.ref('ngsd_base.ngsd_solution_architect').users
            users |= self.env.ref('ngsd_base.ngsd_solution_architect_manager').users
            res['solution_architect_uids']['domain'] = f"[('id', 'in', {users.ids})]"
        return res

    @api.model
    def create(self, vals):
        res = super(CrmLead, self).create(vals)
        res._compute_code()
        mes = 'Cơ hội %s đã được tạo!' % res.name
        ctx = {}
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        report_action = 'crm.crm_lead_action_pipeline'
        tmp = 'ngsd_base.SAnoti'
        action = self.env.ref(report_action)
        ctx.update({'name': res.name, 'link': f'{base_url}/web#id={res.id}&action={action.id}&model=crm.lead&view_type=form'})
        for solution_architect_uid in res.solution_architect_uids:
            email_to = solution_architect_uid.login
            self.env['email.data'].create({
                'lead_id': res.id,
                'tmp': tmp,
                'email_to': email_to,
                'ctx': json.dumps(ctx),
                'state': 'new'
            })
            res.send_notify(mes, solution_architect_uid)
        for team_lead in res.solution_architect_uids.crm_team_ids.user_ids:
            email_to = team_lead.login
            self.env['email.data'].create({
                'lead_id': res.id,
                'tmp': tmp,
                'email_to': email_to,
                'ctx': json.dumps(ctx),
                'state': 'new'
            })
            res.send_notify(mes, team_lead)
        return res

    def write(self, values):
        solution_architect_uid_change = {}
        if 'solution_architect_uids' in values:
            for o in self:
                solution_architect_uid_change[o.id] = o.solution_architect_uids
        res = super(CrmLead, self).write(values)
        lost_stage = self._stage_find(domain=[('is_lost', '=', True)], limit=1)
        if values.get('stage_id') == lost_stage.id:
            for rec in self:
                if not rec.lost_reason_text:
                    raise UserError('Vui lòng điền Lý do thua trước khi chuyển sang thua!')
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        report_action = 'crm.crm_lead_action_pipeline'
        tmp = 'ngsd_base.SAnoti'
        action = self.env.ref(report_action)
        if 'solution_architect_uids' in values:
            for rec in self:
                mes = 'Cơ hội %s đã được tạo!' % rec.name
                if rec.solution_architect_uids:
                    for solution_architect_uid in (rec.solution_architect_uids - solution_architect_uid_change[rec.id]):
                        email_to = solution_architect_uid.login
                        ctx = {'name': rec.name, 'link': f'{base_url}/web#id={rec.id}&action={action.id}&model=crm.lead&view_type=form'}
                        self.env['email.data'].create({
                            'lead_id': rec.id,
                            'tmp': tmp,
                            'email_to': email_to,
                            'ctx': json.dumps(ctx),
                            'state': 'new'
                        })
                        rec.send_notify(mes, solution_architect_uid)
        for rec in self:
            if rec.company_type != 'dmc' or not rec.message_partner_ids:
                continue
            mes = 'Lead %s có cập nhật mới. Vui lòng kiểm tra thông tin' % rec.name
            rec.send_notify(mes, rec.message_partner_ids.user_ids)
        return res

    def action_open_new_tab(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        report_action = 'crm.crm_lead_action_pipeline'
        action = self.env.ref(report_action)
        record_url = f'{base_url}/web#id={self.id}&action={action.id}&model=crm.lead&view_type=form'
        client_action = {
            'type': 'ir.actions.act_url',
            'name': action.name,
            'target': 'new',
            'url': record_url,
        }
        return client_action

    company_id = fields.Many2one(default=lambda self: self.env.company)
    company_type = fields.Char(string='Loại Công ty', related='company_id.company_type')

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super(CrmLead, self).fields_get(allfields, attributes=attributes)
        # bỏ email_from, phone
        lst_fields_ngsd = ['solution_architect_uids', 'role_id', 'budget_approval_date', 'bid_opening_date', 'bid_closing_date', 'kickoff_planned_date', 'project_end_date', 'ngsd_revenue']
        for f in lst_fields_ngsd:
            if f in res:
                res[f]['invisible_domain'] = "[('company_type', '!=', 'ngsd')]"
        # bỏ last_update_note
        lst_fields_no_ngsd = ['compete_id', 'total_revenue']
        for f in lst_fields_no_ngsd:
            if f in res:
                res[f]['invisible_domain'] = "[('company_type', '=', 'ngsd')]"

        if 'priority' in res:
            users = self.env.ref('ngsd_base.group_ngs_head_of_operations').users
            users |= self.env.ref('ngsd_base.group_ngs_board_of_directors').users
            res['priority']['readonly'] = self.env.user not in users
        return res

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        if view_type == 'tree':
            ngsd_company = self.env['res.company'].search([('company_type', '=', 'ngsd')]).ids
            dmc_company = self.env['res.company'].search([('company_type', '=', 'dmc')]).id
            ncs_company = self.env['res.company'].search([('company_type', '=', 'ncs')]).id
            if ngsd_company and len(set(self._context.get('allowed_company_ids', False) + ngsd_company)) != len(self._context.get('allowed_company_ids', False) + ngsd_company):
                view_id = self.env.ref('ngsd_crm.crm_lead_view_tree').id
            elif dmc_company and dmc_company in self._context.get('allowed_company_ids', []):
                if self._context.get('default_type') == 'lead':
                    view_id = self.env.ref('ngsd_crm.crm_lead_view_dmc_lead_tree').id
                else:
                    view_id = self.env.ref('ngsd_crm.crm_lead_view_dmc_tree').id
            elif ncs_company and ncs_company in self._context.get('allowed_company_ids', []):
                view_id = self.env.ref('ngsd_crm.crm_lead_view_ncs_tree').id
            else:
                view_id = self.env.ref('ngsd_crm.crm_lead_view_no_ngsd_tree').id
        res = super(CrmLead, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        return res

    targets_amount = fields.Float('Chỉ tiêu', default=0)
    compete_id = fields.Many2one('compete.lead', 'Tính cạnh tranh')
    lost_reason_text = fields.Text('Lý do thua', readonly=True)

    @api.onchange('compete_id')
    def onchange_compete_id(self):
        if self.compete_id:
            self.priority = self.compete_id.rate

    def _stage_find(self, team_id=False, domain=None, order='sequence, id', limit=1):
        """ Determine the stage of the current lead with its teams, the given domain and the given team_id
            :param team_id
            :param domain : base search domain for stage
            :param order : base search order for stage
            :param limit : base search limit for stage
            :returns crm.stage recordset
        """
        # collect all team_ids by adding given one, and the ones related to the current leads
        team_ids = set()
        if team_id:
            team_ids.add(team_id)
        for lead in self:
            if lead.team_id:
                team_ids.add(lead.team_id.id)
        # generate the domain
        if team_ids:
            search_domain = ['|', ('team_id', '=', False), ('team_id', 'in', list(team_ids))]
        else:
            search_domain = [('team_id', '=', False)]
        # AND with the domain in parameter
        if domain:
            search_domain += list(domain)
        search_domain += [('company_id', 'in', self.company_id.ids)]
        # perform search, return the first found
        return self.env['crm.stage'].search(search_domain, order=order, limit=limit)

    last_update_note = fields.Text('Cập nhật gần nhất', compute='_get_last_update_note', compute_sudo=True)

    @api.depends('x_support_history_ids_no_ngsd', 'x_support_history_ids_no_ngsd.x_note')
    def _get_last_update_note(self):
        for rec in self:
            lasted = rec.x_support_history_ids_no_ngsd.sorted(lambda o: o.x_date or datetime.date(1900, 1, 1), reverse=True)[:1]
            if lasted.x_date:
                rec.last_update_note = f"{lasted.x_date.strftime('%d/%m/%Y')} - {lasted.x_note}"
            else:
                rec.last_update_note = ''

    def send_noti_new(self):
        domain = [('stage_id.x_type', '=', 'new'), ('company_type', '=', 'dmc')]
        if not self:
            self.search(domain)
        else:
            self.filtered_domain(domain)
        for rec in self:
            mes = 'Lead %s chưa được cập nhật!' % rec.name
            rec.send_notify(mes, rec.user_id)

    def check_x_support_history(self):
        leads = self.search([('x_support_history_ids', '=', False), ('company_type', '!=', 'ngsd')])
        for rec in leads:
            mes = 'Lead %s chưa được cập nhật!' % rec.name
            rec.send_notify(mes, rec.user_id)

    perform_quarter = fields.Float('Performance quý', compute="_get_perform_quarter", compute_sudo=True)
    perform_year = fields.Float('Performance năm', compute="_get_perform_year", compute_sudo=True)

    @api.depends('user_id', 'user_id.employee_ids.target_quarter')
    def _get_perform_quarter(self):
        for rec in self:
            rec.perform_quarter = rec.total_revenue / rec.user_id.employee_ids.target_quarter if rec.user_id.employee_ids.target_quarter else 0

    @api.depends('user_id', 'user_id.employee_ids.target_year')
    def _get_perform_year(self):
        for rec in self:
            rec.perform_year = rec.total_revenue / rec.user_id.employee_ids.target_year if rec.user_id.employee_ids.target_year else 0

    x_attach_file = fields.Many2many(string='Tệp đính kèm', comodel_name='ir.attachment')

    data_attachment = fields.Binary(string="Tệp đính kèm")
    data_pdf_preview = fields.Binary(compute='get_data_pdf_preview', compute_sudo=True)
    file_name = fields.Char("file name")

    @api.depends('data_attachment')
    def get_data_pdf_preview(self):
        for rec in self:
            if rec.data_attachment:
                rec.data_pdf_preview = rec.data_attachment
            else:
                rec.data_pdf_preview = False

    def action_set_lost(self, **additional_values):
        """ Lost semantic: probability = 0 or active = False """
        res = self.action_archive()
        lost_stage = self._stage_find(domain=[('is_lost', '=', True)], limit=1)
        if lost_stage:
            additional_values = additional_values or {}
            additional_values['stage_id'] = lost_stage.id
        if additional_values:
            self.write(dict(additional_values))
        return res

    def toggle_active(self):
        res = super(CrmLead, self).toggle_active()
        activated = self.filtered(lambda lead: lead.active)
        if activated:
            activated.write({'lost_reason_text': False})
        return res

    def convert_domain_to_active(self, domain=[]):
        if 'active' in str(domain):
            return self
        return self.with_context(active_test=False)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        self = self.convert_domain_to_active(domain)
        res = super(CrmLead, self).search_read(domain, fields, offset, limit, order)
        return res

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        self = self.convert_domain_to_active(args)
        return super(CrmLead, self)._name_search(name=name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        self = self.convert_domain_to_active(domain)
        return super(CrmLead, self).read_group(domain, fields, groupby, offset, limit, orderby, lazy)

    @api.model
    def search_count(self, args):
        self = self.convert_domain_to_active(args)
        return super(CrmLead, self).search_count(args)

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        self = self.convert_domain_to_active(args)
        return super(CrmLead, self).search(args, offset=offset, limit=limit, order=order, count=count)

