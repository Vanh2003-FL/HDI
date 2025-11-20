from odoo import models, fields, api
from dateutil.relativedelta import relativedelta
from odoo.tools import float_compare, float_is_zero


class KpiKpi(models.Model):
    _name = 'en.kpi.kpi'
    _description = 'Chỉ tiêu KPI'
    _order = 'year desc'

    def button_confirmed(self):
        self.write({'state': 'confirmed'})

    def button_cancel(self):
        self.env['en.kpi.detail'].sudo().search([('kpi_id', 'in', self.ids)]).unlink()
        self.write({'state': 'cancel'})

    def create_kpi_detail(self):
        vals_list = []
        to_create = self.mapped('team_kpi_ids')
        to_create |= self.mapped('sale_kpi_ids')
        for rec in to_create:
            vals_list += [
                dict(kpi_id=rec.kpi_id.id,
                     line_kpi_id=rec.id,
                     type=rec.type,
                     sale_team_id=rec.sale_team_id.id if rec.type == 'team' else False,
                     user_id=rec.user_id.id if rec.type == 'sale' else False,
                     date_from=rec.kpi_id.date_from.replace(year=int(rec.kpi_id.year), day=1, month=distribute.month),
                     date_to=rec.kpi_id.date_to.replace(year=int(rec.kpi_id.year), day=1, month=distribute.month) + relativedelta(months=1) + relativedelta(days=-1),
                     rate=distribute.rate,
                     currency_id=rec.kpi_id.currency_id.id,
                     kpi_sales=distribute.rate * rec.sales,
                     kpi_revenue=distribute.rate * rec.revenue,
                     kpi_invoiced=distribute.rate * rec.invoiced,
                     )
                for distribute in rec.kpi_id.distribute_line_ids]
        self.env['en.kpi.detail'].search([('kpi_id', 'in', self.ids)]).sudo().unlink()
        self.env['en.kpi.detail'].sudo().create(vals_list)
        return self.to_detail()

    is_detailable = fields.Boolean(string='💳', compute_sudo=True, compute='_compute_is_detailable')

    def _compute_is_detailable(self):
        for rec in self:
            rec.is_detailable = True if self.env['en.kpi.detail'].search_count([('kpi_id', 'in', self.ids)]) else False

    def to_detail(self):
        return self.open_form_or_tree_view(action='ngsd_base.kpi_detail_act', records=self.env['en.kpi.detail'].search([('kpi_id', 'in', self.ids)]))

    name = fields.Char(string='Tên', required=True)
    year = fields.Char(string='Năm', required=True, default=lambda self: str(fields.Date.today().year))

    @api.model
    def all_years_selection(self):
        return [(str(i), str(i)) for i in range(fields.Date.today().year - 5, fields.Date.today().year + 6)]

    date_from = fields.Date(string='Ngày bắt đầu')
    date_to = fields.Date(string='Ngày kết thúc')

    # date_from = fields.Date(string='Từ ngày', compute_sudo=True, compute='_compute_based_on_year')
    # date_to = fields.Date(string='Đến ngày', compute_sudo=True, compute='_compute_based_on_year')

    # @api.depends('year')
    # def _compute_based_on_year(self):
    #     for rec in self:
    #         date_from = False
    #         date_to = False
    #         if not rec.year:
    #             rec.date_from = date_from
    #             rec.date_to = date_to
    #             continue
    #         rec.date_from = fields.Date.today().replace(year=int(rec.year), day=1, month=1)
    #         rec.date_to = fields.Date.today().replace(year=int(rec.year), day=1, month=1) + relativedelta(years=1) + relativedelta(days=-1)

    distribute_type = fields.Selection(string='Cách thức phân bổ', selection=[('equal', 'Phân bổ đều'), ('manual', 'Thủ công')], default='equal')
    company_id = fields.Many2one(string='Công ty', comodel_name='res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one(string='Tiền tệ', comodel_name='res.currency', default=lambda self: self.env.company.currency_id)
    state = fields.Selection(string='Trạng thái', selection=[('new', 'Mới'), ('confirmed', 'Đã xác nhận'), ('cancel', 'Hủy')], default='new', readonly=True, copy=False, required=True)
    team_kpi_ids = fields.One2many(string='KPI nhóm', copy=True, comodel_name='en.kpi.line', inverse_name='kpi_id', domain=[('type', '=', 'team')])
    sale_kpi_ids = fields.One2many(string='KPI cá nhân', copy=True, comodel_name='en.kpi.line', inverse_name='kpi_id', domain=[('type', '=', 'sale')])
    distribute_line_ids = fields.One2many(string='Tỷ lệ phân bộ', compute_sudo=True, compute='_compute_distribute_line_ids', store=True, readonly=False, copy=True, comodel_name='en.kpi.rate', inverse_name='kpi_id')

    @api.depends('distribute_type', 'date_from', 'date_to')
    def _compute_distribute_line_ids(self):
        for rec in self:
            distribute_line_ids = [(5, 0, 0)]
            if rec.date_from and rec.date_to:
                start_date = self.date_from + relativedelta(day=1)
                end_date = self.date_to
                current_date = start_date
                months = 0
                while current_date <= end_date:
                    months += 1
                    current_date += relativedelta(months=1)
                rate = 1 / months if rec.distribute_type == 'equal' else 0
                for m in range(months):
                    r_date = start_date + relativedelta(months=m)
                    distribute_line_ids += [
                        Command.create({"quarter": m // 3 + 1, "year": str(r_date.year), "month": r_date.month, "rate": rate, })
                    ]
            rec.distribute_line_ids = distribute_line_ids


class KpiLine(models.Model):
    _name = 'en.kpi.line'
    _description = 'Chi tiết KPI'

    kpi_id = fields.Many2one(string='Chỉ tiêu KPI', comodel_name='en.kpi.kpi', required=True, ondelete='cascade')
    name = fields.Char(string='Tên', compute_sudo=True, compute='_compute_name', store=True, readonly=False)

    @api.depends('kpi_id.name', 'type', 'sale_team_id', 'user_id')
    def _compute_name(self):
        for rec in self:
            rec.name = f'{rec.user_id.name if rec.type == "sale" else rec.sale_team_id.name} {rec.kpi_id.name}'

    sale_team_id = fields.Many2one(string='Nhóm kinh doanh', comodel_name='crm.team', compute_sudo=True, compute='_compute_sale_team_id', store=True, readonly=False)
    user_id = fields.Many2one(string='Nhân viên kinh doanh', comodel_name='res.users', domain="[('crm_team_ids','=?',sale_team_id)]")

    @api.depends('user_id.sale_team_id')
    def _compute_sale_team_id(self):
        for rec in self:
            sale_team_id = rec.sale_team_id
            if rec.user_id:
                sale_team_id = rec.user_id.sale_team_id
            rec.sale_team_id = sale_team_id

    sales = fields.Float(string='Doanh số', default=0)
    revenue = fields.Float(string='Dòng tiền', default=0)
    invoiced = fields.Float(string='Doanh thu', default=0)
    currency_id = fields.Many2one(related='kpi_id.currency_id')
    type = fields.Selection(string='Loại', selection=[('team', 'Nhóm kinh doanh'), ('sale', 'Nhân viên kinh doanh')])


class KpiRate(models.Model):
    _name = 'en.kpi.rate'
    _description = 'Tỷ lệ phân bổ'

    @api.constrains('kpi_id', 'rate')
    def _constrains_kpi_rate(self):
        precision = self.env['decimal.precision'].precision_get('Product Price')
        precision += 2 # thêm 2 số sau dấu ,
        for rec in self:
            if (not float_is_zero(sum(self.search([('kpi_id', '=', rec.kpi_id.id)]).mapped('rate')), precision)
            and not float_is_zero(sum(self.search([('kpi_id', '=', rec.kpi_id.id)]).mapped('rate')) - 1, precision)):
                raise exceptions.ValidationError('Tổng tỷ lệ phân bổ tháng không bằng 100%')

    kpi_id = fields.Many2one(string='Chỉ tiêu KPI', required=True, ondelete='cascade', comodel_name='en.kpi.kpi')
    year = fields.Char(string='Năm')
    quarter = fields.Integer(string='Quý')
    month = fields.Integer(string='Tháng')
    rate = fields.Float(string='Tỷ lệ', default=0)
