from odoo import models, fields, api, _, exceptions
from odoo.exceptions import UserError


class ResPartner(models.Model):
  _inherit = "res.partner"

  bfsi_id = fields.Many2one(string='Phân khúc khách hàng BFSI',
                            comodel_name='en.bfsi')
  technical_field_27310 = fields.Many2many(string='🪙',
                                           relation='partner_with_lead_partner_rel',
                                           column1='src_id', column2='dest_id',
                                           comodel_name='res.partner',
                                           readonly=True, copy=False)

  en_internal = fields.Boolean(string='Nội bộ', default=False, readonly=True,
                               copy=False)
  en_from_lead_ok = fields.Boolean(string='Tạo từ cơ hội', default=False,
                                   readonly=True, copy=False)
  x_code = fields.Char(string='Mã khách hàng')
  x_short = fields.Char(string='Tên viết tắt')
  x_gender = fields.Selection(string='Giới tính',
                              selection=[('male', 'Nam'), ('female', 'Nữ'),
                                         ('other', 'Khác')])
  x_id = fields.Char(string='Số giấy tờ')
  x_id_date = fields.Date(string='Ngày cấp')
  x_id_issue = fields.Char(string='Nơi cấp')

  is_customer = fields.Boolean('Là khách hàng')
  is_supplier = fields.Boolean('Là đơn vị bán')
  is_competitors = fields.Boolean('Là đối thủ cạnh tranh')
  is_manufacturer = fields.Boolean('Là hãng')
  activity_user_ids = fields.Many2many('res.users', string="Người phụ trách",
                                       relation='activity_user_ids',
                                       default=lambda self: [
                                         (6, 0, self.env.user.ids)])

  x_department = fields.Char('Phòng ban')
  name = fields.Char(tracking=True)
  # overwrite field comany_id
  company_id = fields.Many2one(default=lambda self: self.env.company)

  company_type = fields.Selection(default='company')
  company_type_res = fields.Char(related='company_id.company_type',
                                 string="Loại công ty")
  customer_type = fields.Selection(related='type', string='Address Type',
                                   readonly=True, )
  customer_category_id = fields.Many2one('x.customer.category',
                                         string='Mảng khách hàng', copy=False)
  customer_code = fields.Char(string='Mã khách hàng', copy=False, readonly=True)
  customer_group_id = fields.Many2one('x.customer.group',
                                      string='Nhóm khách hàng', copy=False)
  x_note = fields.Text(string='Mô tả')
  x_dob = fields.Date(string='Ngày sinh')

  is_employee = fields.Boolean('Nhân viên', compute='_compute_is_employee',
                               store=True, compute_sudo=True)

  @api.depends('user_ids', 'user_ids.employee_id')
  def _compute_is_employee(self):
    for rec in self:
      # Check if any user linked to this partner has an employee record
      has_employee = False
      if rec.user_ids:
        # Use sudo() to avoid access rights issues and check if any user has employee_id
        employees = rec.user_ids.sudo().mapped('employee_id')
        has_employee = bool(employees)
      rec.is_employee = has_employee

  @api.constrains('vat', 'company_id')
  def check_unique_vat(self):
    for rec in self:
      if not rec.vat:
        continue
      parent_ids = rec.search([('id', 'parent_of', rec.ids)])
      child_ids = rec.search([('id', 'child_of', parent_ids.ids)])
      domain = [('id', 'not in', child_ids.ids), ('vat', '=', rec.vat),
                ('company_id', '=', rec.company_id.id)]
      if rec.is_customer:
        domain += [('is_customer', '=', True)]
      if rec.is_supplier:
        domain += [('is_supplier', '=', True)]
      if rec.is_competitors:
        domain += [('is_competitors', '=', True)]
      if rec.is_manufacturer:
        domain += [('is_manufacturer', '=', True)]
      if rec.search_count(domain):
        raise UserError('Mã số thuế đã tồn tại!')

  @api.model
  def fields_view_get(self, view_id=None, view_type='form', toolbar=False,
      submenu=False):
    if view_type == 'tree':
      ncs_company_ids = self.env['res.company'].search(
          [('company_type', '=', 'ncs')]).ids
      if ncs_company_ids and len(set(self._context.get('allowed_company_ids',
                                                       False) + ncs_company_ids)) != len(
          self._context.get('allowed_company_ids', False) + ncs_company_ids):
        view_id = self.env.ref('ngsd_base.partner_ncs_res_view_tree').id
    res = super(ResPartner, self).fields_view_get(view_id=view_id,
                                                  view_type=view_type,
                                                  toolbar=toolbar,
                                                  submenu=submenu)
    return res

  @api.model_create_multi
  def create(self, vals_list):
    for vals in vals_list:
      if not vals.get('x_code'):
        vals['x_code'] = self.env['ir.sequence'].next_by_code(
          'seq.code.partner.ac')
      if vals.get('is_customer'):
        vals['customer_code'] = self.env['ir.sequence'].next_by_code(
          'ngsd.base.res.partner')
      if vals.get('parent_id'):
        vals['is_customer'] = False
        vals['is_supplier'] = False
        vals['is_competitors'] = False
        vals['is_manufacturer'] = False
      if vals.get('company_id') and vals.get('parent_id'):
        company = self.env['res.company'].browse(vals.get('company_id'))
        if company.company_type == 'ncs' and vals.get('parent_id'):
          vals['type'] = 'contact'

    res = super(ResPartner, self).create(vals_list)
    for rec in res:
      rec.activity_user_ids = [(6, 0, (rec.activity_user_ids.ids or []) + (
            rec.parent_id.activity_user_ids.ids or []))]
    return res

  def _handle_first_contact_creation(self):
    """ On creation of first contact for a company (or root) that has no address, assume contact address
        was meant to be company address """
    parent = self.parent_id.sudo()
    address_fields = self._address_fields()
    if (parent.is_company or not parent.parent_id) and len(
        parent.child_ids) == 1 and \
        any(self[f] for f in address_fields) and not any(
        parent[f] for f in address_fields):
      addr_vals = self._update_fields_values(address_fields)
      parent.update_address(addr_vals)

  @api.model
  def fields_get(self, allfields=None, attributes=None):
    res = super(ResPartner, self).fields_get(allfields, attributes=attributes)
    # if 'customer_type' in res:
    #     ('invoice', 'Địa chỉ xuất hoá đơn') in res['customer_type']['selection'] and res['customer_type']['selection'].remove(('invoice', 'Địa chỉ xuất hoá đơn'))
    #     ('delivery', 'Địa chỉ giao hàng') in res['customer_type']['selection'] and res['customer_type']['selection'].remove(('delivery', 'Địa chỉ giao hàng'))
    return res

  @api.model
  def default_get(self, fields):
    vals = super(ResPartner, self).default_get(fields)
    if vals.get('company_id') and vals.get('type') != 'contact':
      company = self.env['res.company'].browse(vals.get('company_id'))
      if company.company_type == 'ncs':
        vals['type'] = 'contact'

    return vals

  @api.model
  def _name_search(self, name='', args=None, operator='ilike', limit=100,
      name_get_uid=None):
    if self._context.get('view_all_res_partner'):
      self = self.sudo()
    return super(ResPartner, self)._name_search(name=name, args=args,
                                                operator=operator, limit=limit,
                                                name_get_uid=name_get_uid)
