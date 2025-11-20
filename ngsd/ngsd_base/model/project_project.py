import re
from odoo import api, fields, models, _
from datetime import timedelta, datetime, time, date
from dateutil.relativedelta import relativedelta
from collections import defaultdict
from odoo.tools import config, date_utils, get_lang, html2plaintext
from pytz import timezone, UTC
from lxml import etree
import json
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import formatLang


def daterange(start_date, end_date):
  for n in range(int(((end_date + timedelta(days=1)) - start_date).days)):
    yield start_date + timedelta(n)


READONLY_STATES = {
  'approved': [('readonly', True)],
}

org_chart_classes = {
  0: "level-0",
  1: "level-1",
  2: "level-2",
  3: "level-3",
  4: "level-4",
}


class Documents(models.Model):
  _inherit = 'documents.document'

  can_download = fields.Boolean(string='Có thể tải xuống',
                                compute='_compute_can_download')

  @api.depends_context('uid')
  @api.depends('folder_id')
  def _compute_can_download(self):
    for rec in self:
      rec.can_download = rec.folder_id.can_download


class DocumentsFolder(models.Model):
  _inherit = 'documents.folder'

  group_ids = fields.Many2many(
      default=lambda self: self.env.user.from_groups_with_love)
  read_group_ids = fields.Many2many(
      default=lambda self: self.env.user.from_groups_with_love)

  role_write_ids = fields.Many2many('en.role', 'folder_role_1',
                                    string='Vai trò KHNL được ghi')
  employee_write_ids = fields.Many2many('hr.employee', 'folder_employee_1',
                                        string='Nhân sự KHNL được ghi')
  role_read_ids = fields.Many2many('en.role', 'folder_role_2',
                                   string='Vai trò KHNL được xem')
  employee_read_ids = fields.Many2many('hr.employee', 'folder_employee_2',
                                       string='Nhân sự KHNL được xem')

  employee_write_role_ids = fields.Many2many('hr.employee',
                                             'folder_write_employee_1',
                                             string='Nhân sự KHNL ghi theo vai trò',
                                             compute='_compute_employee_write_role',
                                             compute_sudo=True, store=True)
  employee_read_role_ids = fields.Many2many('hr.employee',
                                            'folder_read_employee_1',
                                            string='Nhân sự KHNL xem theo vai trò',
                                            compute='_compute_employee_read_role',
                                            compute_sudo=True, store=True)

  domain_role_ids = fields.Many2many('en.role',
                                     string='Vai trò KHNL được ghi domain',
                                     compute='_compute_role_employee',
                                     compute_sudo=True)
  domain_employee_ids = fields.Many2many('hr.employee',
                                         string='Nhân sự KHNL được ghi domain',
                                         compute='_compute_role_employee',
                                         compute_sudo=True)

  all_employee_read = fields.Boolean('Tất cả thành viên dự án được xem')

  def _compute_role_employee(self):
    for rec in self:
      rec.domain_role_ids = False
      rec.domain_employee_ids = False
      if rec.en_project_id and rec.en_project_id.en_resource_id:
        for line in rec.en_project_id.en_resource_id.order_line:
          rec.domain_role_ids = [(4, line.role_id.id)]
          rec.domain_employee_ids = [(4, line.employee_id.id)]

  @api.depends('role_write_ids')
  def _compute_employee_write_role(self):
    for rec in self:
      rec.employee_write_role_ids = False
      if rec.en_project_id and rec.en_project_id.en_resource_id and rec.role_write_ids:
        for line in rec.en_project_id.en_resource_id.order_line.filtered(
            lambda x: x.role_id.id in rec.role_write_ids.ids):
          rec.employee_write_role_ids = [(4, line.employee_id.id)]

  @api.depends('role_read_ids')
  def _compute_employee_read_role(self):
    for rec in self:
      rec.employee_read_role_ids = False
      if rec.en_project_id and rec.en_project_id.en_resource_id and rec.role_read_ids:
        for line in rec.en_project_id.en_resource_id.order_line.filtered(
            lambda x: x.role_id.id in rec.role_read_ids.ids):
          rec.employee_read_role_ids = [(4, line.employee_id.id)]

  @api.onchange('parent_folder_id')
  def _onchange_parent_folder_id(self):
    for rec in self:
      if not rec.parent_folder_id: continue
      if not rec.role_write_ids:
        rec.role_write_ids = [(6, 0, rec.parent_folder_id.role_write_ids.ids)]
      if not rec.role_read_ids:
        rec.role_read_ids = [(6, 0, rec.parent_folder_id.role_read_ids.ids)]
      if not rec.employee_write_ids:
        rec.employee_write_ids = [(6, 0, rec.employee_write_ids.ids)]
      if not rec.employee_read_ids:
        rec.employee_read_ids = [(6, 0, rec.employee_read_ids.ids)]
      if not rec.all_employee_read:
        rec.all_employee_read = True

  can_download = fields.Boolean(string='Có thể tải xuống',
                                compute='_compute_can_download')

  @api.depends_context('uid')
  @api.depends('employee_write_ids', 'employee_write_role_ids')
  def _compute_can_download(self):
    for rec in self:
      rec.can_download = self.env.user.employee_id in (
          rec.employee_write_ids | rec.employee_write_role_ids | rec.employee_read_ids | rec.employee_read_role_ids) or rec.check_access_rights(
          'read', raise_exception=False)


class ProjectProjectStage(models.Model):
  _inherit = 'project.project.stage'

  en_state = fields.Selection(string='Trạng thái dự án',
                              selection=[('draft', 'Dự kiến'),
                                         ('wait_for_execution',
                                          'Chờ thực hiện'),
                                         ('doing', 'Đang thực hiện'),
                                         ('pending', 'Trì hoãn'),
                                         ('finish', 'Hoàn thành'),
                                         ('complete', 'Đóng'),
                                         ('cancel', 'Hủy bỏ')], required=True)
  en_required_field_ids = fields.Many2many(string='Thông tin bắt buộc',
                                           comodel_name='ir.model.fields',
                                           domain="[('model','=','project.project')]")

  @api.constrains('en_state')
  def _en_constrains_en_state(self):
    if any(self.search_count([('en_state', '=', rec.en_state)]) > 1 for rec in
           self):
      raise exceptions.ValidationError('Đã tồn tại Giai đoạn nhiệm vụ này!')


class Bmm(models.Model):
  _name = 'en.bmm'
  _description = 'BMM'
  _order = 'date'

  def write(self, values):
    bmm_after = values.get('bmm', False)
    expense_after = values.get('expense', False)
    text_messeage = """"""
    if bmm_after and expense_after:
      text_messeage = f"""
                <li>BMM: {self.bmm} → {bmm_after}</li>
                <li>Chi phí: {formatLang(self.env, self.expense, currency_obj=self.env.company.currency_id)} → {formatLang(self.env, expense_after, currency_obj=self.env.company.currency_id)}</li>
            """
    elif bmm_after:
      text_messeage = f"""
                            <li>BMM: {self.bmm} → {bmm_after}</li>
                        """
    elif expense_after:
      text_messeage = f"""
                            <li>Chi phí: {formatLang(self.env, self.expense, currency_obj=self.env.company.currency_id)} → {formatLang(self.env, expense_after, currency_obj=self.env.company.currency_id)}</li>
                        """
    if text_messeage:
      subject = f'BMM {self.month_txt} đã thay đổi'
      self.project_id.message_post(body=text_messeage, subject=subject)
    return super(Bmm, self).write(values)

  project_id = fields.Many2one(string='Dự án', comodel_name='project.project',
                               required=True, ondelete='cascade')
  date = fields.Date(string='Ngày', readonly=True, copy=False)
  month_txt = fields.Char(string='Tháng', readonly=True, copy=False)
  bmm = fields.Float(string='BMM', default=0)


class InfProject(models.Model):
  _name = 'en.inf.project'
  _description = 'Thông tin dự án'

  project_id = fields.Many2one(string='Dự án', comodel_name='project.project',
                               required=True, ondelete='cascade')
  type = fields.Char(string='Loại')
  value = fields.Float(string='Giá trị', default=0)
  technical_field_28197 = fields.Date(string='🗓️')
  date_start = fields.Date(string='Ngày bắt đầu',
                           related='project_id.date_start', store=True)
  date = fields.Date(string='Ngày kết thúc', related='project_id.date',
                     store=True)

  @api.model
  def read_group(self, domain, fields, groupby, offset=0, limit=None,
      orderby=False, lazy=True):
    self.sudo().search(domain).read()
    return super().read_group(domain, fields, groupby, offset=offset,
                              limit=limit, orderby=orderby, lazy=lazy)

  def read(self, fields=None, load='_classic_read'):
    for rec in self:
      if not rec.technical_field_28197: continue
      if rec.type == 'BMM':
        value = sum(rec.project_id.en_bmm_ids.filtered(
            lambda x: x.date == rec.technical_field_28197).mapped('bmm'))
        rec.sudo().write({'value': value})
      if rec.type == 'Plan':
        a = rec.technical_field_28197
        b = rec.technical_field_28197 + relativedelta(day=1) + relativedelta(
            months=1) + relativedelta(days=-1)
        value = 0
        for line in rec.project_id.en_resource_id.order_line:
          if line.date_start > b: continue
          if line.date_end < a: continue
          employee = line.employee_id
          for date_step in date_utils.date_range(
              datetime.combine(line.date_start + relativedelta(day=1),
                               time.min), datetime.combine(
                  line.date_end + relativedelta(day=1) + relativedelta(
                      months=1) + relativedelta(days=-1), time.max),
              relativedelta(months=1)):
            compared_from = (date_step + relativedelta(day=1)).date()
            compared_to = (
                date_step + relativedelta(months=1, day=1, days=-1)).date()
            x = 0
            y = 0
            tech_data = self.env[
              'en.technical.model'].convert_daterange_to_data(employee,
                                                              datetime.combine(
                                                                  compared_from,
                                                                  time.min),
                                                              datetime.combine(
                                                                  compared_to,
                                                                  time.max))
            for d in tech_data:
              tech = tech_data.get(d)
              if tech and tech.get('tech') != 'off':
                y += 1
              if tech and tech.get(
                  'number') and a <= d <= b and line.date_start <= d <= line.date_end:
                x += tech.get('number') / 8
            value += x / y if y else 0
        rec.sudo().write({'value': value})
      if rec.type == 'MM actual':
        a = rec.technical_field_28197
        b = rec.technical_field_28197 + relativedelta(day=1) + relativedelta(
            months=1) + relativedelta(days=-1)
        value = sum(line.mm for line in rec.project_id.task_ids.filtered(
            lambda x: x.en_wbs_state == 'approved').mapped(
            'timesheet_ids').filtered(
            lambda x: x.en_state == 'approved' and a <= x.date <= b))
        rec.sudo().write({'value': value})
    return super().read(fields, load)


class EnriskSLAChange(models.Model):
  _name = 'en.risk.sla.change'
  _description = 'Risk SLA Change'

  en_risk_id = fields.Many2one('en.risk', required=1, ondelete='cascade',
                               index=True)
  field = fields.Char(index=True)
  old_state = fields.Char(index=True)
  new_state = fields.Char(index=True)


class EnriskSLA(models.Model):
  _name = 'en.risk.sla'
  _description = 'Chính sách SLA'

  action = fields.Selection(selection=[
    ('find', 'Xác định thông tin'),
    ('en_cf', 'CSH đánh giá'),
    ('quota_check', 'Định mức'),
    ('check', 'Kiểm tra thông tin'),
    ('suggest', 'Đề xuất biện pháp'),
    ('bod_check', 'Lãnh đạo đánh giá'),
    ('confirm', 'Xác nhận'),
  ], string='Hành động', required=1)
  time_limit = fields.Integer('Thời hạn (giờ)', required=1)
  type = fields.Selection(selection=[('create', 'Rủi ro được tạo'), ('old_done',
                                                                     'Bước trước được hoàn thành')],
                          string='Mốc thời gian', required=1)

  @api.constrains('action')
  def cehck_unique_action(self):
    for rec in self:
      if self.search_count([('action', '=', rec.action), ('id', '!=', rec.id)]):
        raise UserError('Hành động này đã được cấu hình!')


class ProjectProject(models.Model):
  _inherit = 'project.project'

  @api.model
  def fields_view_get(self, view_id=None, view_type='form', toolbar=False,
      submenu=False):
    res = super().fields_view_get(view_id=view_id, view_type=view_type,
                                  toolbar=toolbar, submenu=submenu)
    if view_type != 'form':
      return res
    doc = etree.XML(res['arch'])
    if not self.env.user.has_group(
        'ngsd_base.group_tpvh,ngsd_base.group_pm,ngsd_base.group_tptc,ngsd_base.group_qam,ngsd_base.group_gdkndu,ngsd_base.group_gdkv,ngsd_base.group_tppmo,ngsd_base.group_tk,ngsd_base.group_vpm'):
      for node in doc.xpath("//field[@name='en_resource_ids']"):
        node.getparent().remove(node)
    res['arch'] = etree.tostring(doc, encoding='unicode')
    return res

  technical_field_28187 = fields.Char(string='Nguồn lực thực tế',
                                      compute_sudo=True,
                                      compute='_compute_technical_field_28187',
                                      readonly=True)
  name_partner = fields.Char('Khách hàng', related='partner_id.display_name',
                             stored=True)
  can_view_draft = fields.Boolean(compute='_compute_can_view_draft',
                                  search='_search_can_view_draft')

  @api.depends_context('uid')
  def _compute_can_view_draft(self):
    for rec in self:
      rec.can_view_draft = self.env.user.has_group(
          'base.group_system,ngsd_base.group_qal')

  def _search_can_view_draft(self, operator, value):
    if self.env.user.has_group('base.group_system,ngsd_base.group_qal'):
      return []
    else:
      return [('id', '=', False)]

  @api.depends('task_ids.timesheet_ids.en_total_amount')
  def _compute_technical_field_28187(self):
    for rec in self:
      total_hours = sum(line.en_total_amount for line in
                        self.env['account.analytic.line'].sudo().search(
                            [('project_id', '=', rec.id),
                             ('en_state', '=', 'approved')]))
      technical_field_28187 = total_hours / 8 / rec.mm_rate if rec.mm_rate else 0
      technical_field_28187 += sum(rec.en_history_resource_ids.mapped('actual'))
      rec.technical_field_28187 = str(round(technical_field_28187, 2))

  def to_project_dashboard(self):
    return {
      'name': 'Dashboard Dự án',
      'res_model': 'en.inf.project',
      'type': 'ir.actions.act_window',
      'view_mode': 'graph',
      'context': {
        'search_default_project_id': self.id
      },
    }

  en_plan = fields.Float(string='Plan', compute_sudo=True,
                         compute='_compute_en_plan')

  @api.depends('en_resource_ids', 'en_resource_ids.state',
               'en_resource_ids.order_line.mm')
  def _compute_en_plan(self):
    for rec in self:
      en_plan = 0
      en_resource_id = self.env['en.resource.planning']
      for resource in rec.en_resource_ids:
        if resource.state == 'approved':
          en_resource_id = resource
      en_plan += sum(en_resource_id.order_line.mapped('mm'))
      rec.en_plan = en_plan

  en_mm_actual = fields.Float(string='MM actual', compute_sudo=True,
                              compute='_compute_en_mm_actual')

  @api.depends('task_ids.timesheet_ids.mm')
  def _compute_en_mm_actual(self):
    for rec in self:
      en_mm_actual = 0
      en_mm_actual += sum(line.mm for line in
                          rec.task_ids.mapped('timesheet_ids').filtered(
                              lambda x: x.en_state == 'approved'))
      rec.en_mm_actual = en_mm_actual

  total_timesheet_time = fields.Integer(groups='base.group_user')

  def en_do(self):
    return {'type': 'ir.actions.act_window_close'}

  def en_to_bmm(self):
    view_id = self.env.ref('ngsd_base.project_project_28105_form').id
    return {
      'type': 'ir.actions.act_window',
      'view_mode': 'form',
      'views': [(view_id, 'form')],
      'res_model': self._name,
      'view_id': view_id,
      'res_id': self.id,
      'target': 'new'
    }

  en_real_start_date = fields.Datetime(string='Ngày bắt đầu thực tế',
                                       readonly=True)
  en_real_end_date = fields.Datetime(string='Ngày kết thúc thực tế',
                                     readonly=True)

  date_start = fields.Date(required=True)
  date = fields.Date(required=True, tracking=True)
  mm_rate = fields.Float(string='Đơn vị quy đổi MM', required=False)
  mm_conversion = fields.Float(string='MM quy đổi của dự án',
                               compute='_compute_mm_conversion')

  # @api.constrains('mm_rate')
  # def _onchange_mm_rate(self):
  #     for rec in self:
  #         if rec.mm_rate <= 0:
  #             raise ValidationError('Đơn vị quy đổi MM phải lớn hơn 0')

  @api.depends('en_resource_ids', 'en_resource_ids.state',
               'en_resource_ids.mm_conversion')
  def _compute_mm_conversion(self):
    for rec in self:
      rec.mm_conversion = rec.en_resource_ids.filtered(
          lambda x: x.state == 'approved').mm_conversion or 0

  def button_view_qdtlda(self):
    return self.env.ref('ngsd_base.report_qdtlda_action').report_action(self)

  def button_view_qddcda(self):
    return self.env.ref('ngsd_base.report_qddcda_action').report_action(self)

  @api.model
  def _name_search(self, name, args=None, operator='ilike', limit=100,
      name_get_uid=None):
    if name:
      return self._search(Domain.AND(
          [['|', ('en_code', operator, name), ('name', operator, name)], args]),
          limit=limit, access_rights_uid=name_get_uid)
    res = super()._name_search(name, args, operator, limit, name_get_uid)
    return res

  # Remove problematic analytic_account_id redefinition for Odoo 18 compatibility
  show_wbs_tab = fields.Boolean(compute='compute_show_wbs_tab')
  is_internal = fields.Boolean(string='Dự án nội bộ')

  @api.depends_context('uid')
  @api.depends('en_resource_ids')
  def compute_show_wbs_tab(self):
    for rec in self:
      show_wbs_tab = False
      if self.env.user.has_group(
          'ngsd_base.group_tpvh,ngsd_base.group_qam,ngsd_base.group_pm,ngsd_base.group_gdkndu,ngsd_base.group_gdkv,ngsd_base.group_tppmo,ngsd_base.group_tk,ngsd_base.group_vpm,ngsd_base.ngsd_sale'):
        show_wbs_tab = True
      if self.env.user.has_group(
          'ngsd_base.group_tvda') and self.env.user.employee_id in rec.sudo().en_resource_ids.order_line.employee_id:
        show_wbs_tab = True
      rec.show_wbs_tab = show_wbs_tab

  show_resource_tab = fields.Boolean(compute='compute_show_resource_tab')

  @api.depends_context('uid')
  @api.depends('en_resource_ids')
  def compute_show_resource_tab(self):
    for rec in self:
      show_resource_tab = False
      if self.env.user.has_group(
          'ngsd_base.group_tpvh,ngsd_base.group_pm,ngsd_base.group_tptc,ngsd_base.group_qam,ngsd_base.group_gdkndu,ngsd_base.group_gdkv,ngsd_base.group_tppmo,ngsd_base.group_tk,ngsd_base.group_vpm,ngsd_base.ngsd_sale'):
        show_resource_tab = True
      if self.env.user.has_group(
          'ngsd_base.group_tvda') and self.env.user.employee_id in rec.sudo().en_resource_ids.order_line.employee_id:
        show_resource_tab = True
      rec.show_resource_tab = show_resource_tab

  igone_overload = fields.Boolean(default=False)
  user_id = fields.Many2one(default=None)
  billable_percentage = fields.Integer(groups='base.group_user')
  en_area_id = fields.Many2one(string='Khu vực', comodel_name='en.name.area')
  en_block_id = fields.Many2one(string='Khối', comodel_name='en.name.block',
                                domain="[('area_id', '=?', en_area_id)]")
  en_bmm_ids = fields.One2many(string='BMM', comodel_name='en.bmm',
                               inverse_name='project_id', compute=False,
                               store=True, readonly=False)

  @api.onchange('date_start', 'date')
  def en_onchange_date_start_date(self):
    if self.date_start and self.date and self.date_start > self.date:
      return {'warning': {
        'title': 'Cảnh báo',
        'message': f'Ngày bắt đầu phải nhỏ hơn ngày kết thúc!'
      }}

  @api.onchange('date_start', 'date')
  def _compute_en_bmm_ids(self):
    for rec in self:
      if not rec.date_start or not rec.date:
        rec.en_bmm_ids = [(5, 0, 0)]
        continue
      datetime_start = datetime.combine(min([rec.date_start, rec.date]),
                                        time.min).replace(day=1)
      datetime_end = datetime.combine(max([rec.date_start, rec.date]),
                                      time.max).replace(day=1)
      matched_bmm = self.env['en.bmm']
      en_bmm_ids = []
      for date_step in date_utils.date_range(datetime_start, datetime_end,
                                             relativedelta(months=1)):
        match_month_bmm = rec.en_bmm_ids.filtered(
            lambda b: b.month_txt == date_step.strftime('%m/%Y'))
        if match_month_bmm:
          matched_bmm |= match_month_bmm
        else:
          en_bmm_ids += [(0, 0, {'date': date_step.date(),
                                 'month_txt': date_step.strftime('%m/%Y'),
                                 'bmm': 0})]
      if rec.en_bmm_ids - matched_bmm:
        en_bmm_ids += [(2, m.id) for m in (rec.en_bmm_ids - matched_bmm)]
      if en_bmm_ids:
        rec.en_bmm_ids = en_bmm_ids

  en_opp = fields.Many2one(comodel_name='crm.lead')
  task_count = fields.Integer(compute_sudo=True)
  task_count_with_subtasks = fields.Integer(compute_sudo=True)

  technical_field_27795 = fields.Boolean(string='🚑',
                                         compute='_compute_technical_field_27795',
                                         compute_sudo=True)

  @api.depends('en_resource_ids.state')
  def _compute_technical_field_27795(self):
    for rec in self:
      technical_field_27795 = False
      if rec.en_resource_ids and any(
          r.state == 'approved' for r in rec.en_resource_ids):
        technical_field_27795 = True
      rec.technical_field_27795 = technical_field_27795

  def button_new_wbs(self):
    action = self.open_form_or_tree_view('ngsd_base.wbs_act', False, False,
                                         {'default_project_id': self.id,
                                          'default_resource_plan_id': self.en_resource_id.id,
                                          'default_user_id': self.user_id.id},
                                         'Tạo WBS')
    action['views'] = [(False, 'form')]
    action['context'] = {'create': 0, 'default_project_id': self.id,
                         'default_resource_plan_id': self.en_resource_id.id,
                         'default_user_id': self.user_id.id}
    return action

  type_ids = fields.Many2many(
      default=lambda self: self.env['project.task.type'].search(
          [('en_mark', '!=', 'b'), ('en_mark', '!=', False),
           ('user_id', '=', False)], order='en_mark asc') | self.env[
                             'project.task.type'].search(
          [('en_mark', '=', 'b'), ('en_mark', '!=', False),
           ('user_id', '=', False)], order='en_mark asc'))

  en_problem_ids = fields.One2many(string='Các vấn đề',
                                   comodel_name='en.problem',
                                   inverse_name='project_id')
  en_problem_count = fields.Integer(string='Các vấn đề', compute_sudo=True,
                                    compute='_compute_en_problem_count')
  first_date = fields.Date(string='Ngày kết thúc', readonly=1, copy=False)
  old_pending_stage_id = fields.Many2one('project.project.stage', readonly=1,
                                         copy=False)

  @api.depends('en_problem_ids')
  def _compute_en_problem_count(self):
    for rec in self:
      rec.en_problem_count = len(rec.en_problem_ids)

  def button_en_problem_act(self):
    return self.open_form_or_tree_view('ngsd_base.en_problem_act', False,
                                       self.en_problem_ids,
                                       {'default_project_id': self.id})

  def button_project_account_report_wizard_act(self):
    return self.open_form_or_tree_view(
        'account_reports.project_account_report_wizard_act', False, False,
        {'default_project_id': self.id},
        'Kế hoạch nguồn lực sử dụng trong dự án',
        'new')

  def new_resource(self):
    return self.open_form_or_tree_view('ngsd_base.resource_planning_act', False,
                                       False, {'default_name': self.name,
                                               'default_project_id': self.id,
                                               'allow_date_end': not self.en_resource_ids},
                                       'Tạo kế hoạch NL', 'current')

  def new_quality_control(self):
    return self.open_form_or_tree_view('ngsd_base.quality_control_act', False,
                                       False, {'default_name': self.name,
                                               'default_project_id': self.id,
                                               'allow_date_end': not self.en_resource_ids},
                                       'Tạo KSCL', 'current')

  def button_en_wait_for_execution(self):
    for rec in self:
      if rec.en_state == 'draft': rec.stage_id = self.env[
        'project.project.stage'].search(
          [('en_state', '=', 'wait_for_execution')], limit=1)

  def button_en_doing(self):
    for rec in self:
      if rec.en_state == 'wait_for_execution':
        rec.en_real_start_date = fields.Datetime.now()
        rec.stage_id = self.env['project.project.stage'].search(
            [('en_state', '=', 'doing')], limit=1)

  def button_en_complete(self):
    for rec in self:
      if rec.en_state == 'doing':
        rec.en_real_end_date = fields.Datetime.now()
        rec.stage_id = self.env['project.project.stage'].search(
            [('en_state', '=', 'complete')], limit=1)

  def button_en_cancel(self):
    for rec in self:
      if rec.en_state in ['draft', 'wait_for_execution', 'doing']:
        risk_stage_cancel = self.env['en.risk.stage'].search(
            [('name', '=', 'Hủy')], limit=1)
        if not risk_stage_cancel:
          raise UserError('Chưa thiết lập Tình trạng "Hủy"')
        rec.en_resource_ids.filtered(
            lambda r: r.state in ['draft', 'to_approve']).write(
            {'state': 'refused'})
        rec.en_resource_ids.filtered(lambda r: r.state in ['approved']).write(
            {'state': 'expire'})
        rec.en_wbs_ids.filtered(
            lambda r: r.state in ['draft', 'awaiting']).write(
            {'state': 'refused'})
        rec.en_wbs_ids.filtered(lambda r: r.state in ['approved']).write(
            {'state': 'inactive'})
        self.env['account.analytic.line'].search([('project_id', '=', self.id),
                                                  ('en_state', 'not in',
                                                   ['approved',
                                                    'cancel'])]).write(
            {'en_state': 'cancel'})
        self.env['en.hr.overtime'].search([('task_id.project_id', '=', self.id),
                                           ('state', 'not in',
                                            ['approved', 'cancel'])]).write(
            {'state': 'cancel'})
        self.env['en.project.document'].search([('project_id', '=', self.id),
                                                ('state', 'not in',
                                                 ['done', 'cancelled'])]).write(
            {'state': 'cancelled'})
        self.env['en.risk'].search([('project_id', '=', self.id),
                                    ('stage_id', '!=',
                                     risk_stage_cancel.id)]).write(
            {'stage_id': risk_stage_cancel.id})
        self.env['en.problem'].search([('project_id', '=', self.id),
                                       ('stage_id', '!=',
                                        risk_stage_cancel.id)]).write(
            {'stage_id': risk_stage_cancel.id})
        rec.stage_id = self.env['project.project.stage'].search(
            [('en_state', '=', 'cancel')], limit=1)

  def button_pending(self):
    stage_id = self.env['project.project.stage'].search(
        [('en_state', '=', 'pending')], limit=1)
    for rec in self:
      if rec.en_state in ['draft', 'wait_for_execution', 'doing']:
        rec.write({
          'stage_id': stage_id,
          'old_pending_stage_id': rec.stage_id,
        })

  def button_continue(self):
    for rec in self:
      if rec.en_state == 'pending':
        rec.write({
          'stage_id': rec.old_pending_stage_id,
          'old_pending_stage_id': False,
        })

  en_state = fields.Selection(string='Trạng thái', related='stage_id.en_state')

  en_risk_ids = fields.One2many(string='Rủi ro/Cơ hội', comodel_name='en.risk',
                                inverse_name='project_id')
  en_risk_count = fields.Integer(string='Rủi ro/Cơ hội', compute_sudo=True,
                                 compute='_compute_en_risk_count')

  @api.depends('en_risk_ids')
  def _compute_en_risk_count(self):
    for rec in self:
      rec.en_risk_count = len(rec.en_risk_ids)

  def to_risk(self):
    return self.open_form_or_tree_view('ngsd_base.risk_act', False,
                                       self.en_risk_ids,
                                       {'default_project_id': self.id})

  label_tasks = fields.Char(default='Công việc')

  def unlink(self):
    documents = self.env['documents.document'].sudo().search(
        [('folder_id', 'child_of', self.en_folder_ids.ids)])
    folders = self.env['documents.folder'].sudo().search(
        [('id', 'parent_of', documents.mapped('folder_id').ids)])
    if self.en_folder_ids: self.env['documents.folder'].sudo().search(
        [('id', 'child_of', self.en_folder_ids.ids),
         ('id', 'not in', folders.ids)]).sudo().unlink()
    if documents: documents.sudo().write({'active': False})
    if folders: folders.sudo().write({'active': False})
    return super().unlink()

  en_folder_ids = fields.One2many(string='Thư mục',
                                  comodel_name='documents.folder',
                                  inverse_name='en_project_id')
  en_folder_count = fields.Integer(string='Thư mục', compute_sudo=True,
                                   compute='_compute_en_folder_count')

  @api.depends('en_folder_ids')
  def _compute_en_folder_count(self):
    for rec in self:
      rec.en_folder_count = len(rec.en_folder_ids)

  def to_folder(self):
    action = self.env["ir.actions.act_window"]._for_xml_id(
        'documents.document_action')
    action['context'] = {'default_en_project_id': self.id}
    action['domain'] = [('folder_id.en_project_id', '=', self.id)]
    return action

  @api.model_create_multi
  def create(self, vals_list):
    for vals in vals_list:
      if vals.get('date'):
        vals['first_date'] = vals['date']
    res = super().create(vals_list)
    for rec in res:
      dvals = {
        'name': rec.name,
        'en_project_id': rec.id,
        'technical_field_27203': True,
        'description': '<p style="margin-bottom: 0px;"></p><center><p>Thư mục tạo tự động của dự án</p></center>'
      }
      self.env['documents.folder'].sudo().create(dvals)
      a = self.env['ir.model.data'].sudo().search(
          [('model', '=', 'project.project'), ('res_id', '=', rec.id)])
      if not a:
        self.env['ir.model.data'].sudo().create(
            {'model': 'project.project', 'name': rec.en_code, 'res_id': rec.id,
             'module': '__import__'})
      else:
        a.sudo().write(
            {'model': 'project.project', 'name': rec.en_code, 'res_id': rec.id,
             'module': '__import__'})
      if rec.stage_id.en_state == 'wait_for_execution':
        self.env['en.inf.project'].sudo().search(
            [('project_id', '=', rec.id)]).sudo().unlink()
        for r in rec.en_bmm_ids:
          self.env['en.inf.project'].sudo().create(
              {'technical_field_28197': r.date, 'project_id': rec.id,
               'type': 'BMM'})
          self.env['en.inf.project'].sudo().create(
              {'technical_field_28197': r.date, 'project_id': rec.id,
               'type': 'Plan'})
          self.env['en.inf.project'].sudo().create(
              {'technical_field_28197': r.date, 'project_id': rec.id,
               'type': 'MM actual'})
    return res

  def write(self, vals):
    if 'user_id' in vals:
      for rec in self:
        rec.sudo().message_unsubscribe(partner_ids=rec.user_id.partner_id.ids)
    res = super().write(vals)
    if 'user_id' in vals:
      for rec in self:
        rec.message_subscribe(partner_ids=rec.user_id.partner_id.ids)
    if 'show_import_button' in vals:
      if not self.env.user.has_group('base.group_system'):
        raise UserError('Bạn không có quyền sửa trường import')
    if 'name' in vals:
      self.mapped('en_folder_ids').filtered(
          lambda x: x.technical_field_27203).sudo().write(
          {'name': vals.get('name')})
    if 'en_code' in vals:
      for rec in self:
        a = self.env['ir.model.data'].sudo().search(
            [('model', '=', 'project.project'), ('res_id', '=', rec.id)])
        if not a:
          self.env['ir.model.data'].sudo().create(
              {'model': 'project.project', 'name': rec.en_code,
               'res_id': rec.id, 'module': '__import__'})
        else:
          a.sudo().write({'model': 'project.project', 'name': rec.en_code,
                          'res_id': rec.id, 'module': '__import__'})
    if 'date' in vals:
      for rec in self:
        if rec.first_date:
          continue
        rec.first_date = rec.date
    if 'stage_id' in vals:
      for rec in self:
        if rec.stage_id.en_state == 'wait_for_execution':
          self.env['en.inf.project'].sudo().search(
              [('project_id', '=', rec.id)]).sudo().unlink()
          for r in rec.en_bmm_ids:
            self.env['en.inf.project'].sudo().create(
                {'technical_field_28197': r.date, 'project_id': rec.id,
                 'type': 'BMM'})
            self.env['en.inf.project'].sudo().create(
                {'technical_field_28197': r.date, 'project_id': rec.id,
                 'type': 'Plan'})
            self.env['en.inf.project'].sudo().create(
                {'technical_field_28197': r.date, 'project_id': rec.id,
                 'type': 'MM actual'})

    return res

  def _compute_task_count(self):
    task_data = self.env['project.task'].read_group(
        [('project_id', 'in', self.ids),
         ('en_wbs_state', '=', 'approved'),
         '|',
         ('stage_id.fold', '=', False),
         ('stage_id', '=', False)],
        ['project_id', 'project_id:count'], ['project_id'])
    result_wo_subtask = defaultdict(int)
    result_with_subtasks = defaultdict(int)
    for data in task_data:
      result_wo_subtask[data['project_id'][0]] += data['project_id_count']
      result_with_subtasks[data['project_id'][0]] += data['project_id_count']
    for project in self:
      project.task_count = result_wo_subtask[project.id]
      project.task_count_with_subtasks = result_with_subtasks[project.id]

  @api.constrains('stage_id')
  def _constrains_required_by_stage(self):
    self = self.sudo()
    for rec in self:
      if not rec.stage_id.en_required_field_ids:
        continue
      missed_fields = []
      for req in rec.stage_id.en_required_field_ids:
        if not rec[req.name]:
          missed_fields += [
            req.with_context(lang=self.env.user.lang).field_description]
      if missed_fields:
        raise exceptions.ValidationError(
            f"Chưa điền các thông tin bắt buộc tại {', '.join(missed_fields)}")

  en_link_system = fields.Char(string='Hệ thống liên kết')
  en_customer_type_id = fields.Many2one(string='Loại khách hàng',
                                        comodel_name='en.customer.type')
  en_contract_type_id = fields.Many2one(string='Loại hợp đồng',
                                        comodel_name='project.type.source')
  en_contract_number = fields.Char(string='Số hợp đồng')
  en_branch_id = fields.Many2one(string='Ngành', comodel_name='en.branch')
  currency_id = fields.Many2one(string='Đơn vị tiền tệ',
                                comodel_name='res.currency', readonly=False,
                                related=None, store=True, default=lambda
        self: self.env.company.currency_id)
  en_project_manager_id = fields.Many2one(string='Giám đốc dự án',
                                          comodel_name='res.users')
  en_project_implementation_id = fields.Many2one(string='Giám đốc khối',
                                                 comodel_name='res.users')
  en_project_block_id = fields.Many2one(string='Giám đốc Trung tâm',
                                        comodel_name='res.users')
  en_project_qa_id = fields.Many2one(string='QA dự án',
                                     comodel_name='res.users',
                                     default=lambda self: self.env.user)
  en_project_sale_id = fields.Many2one(string='Sales', comodel_name='res.users')
  en_project_accountant_id = fields.Many2one(string='Kế toán',
                                             comodel_name='res.users')
  en_bmm = fields.Float(string='BMM', default=0, compute='_compute_en_bmm',
                        store=True)

  @api.depends('en_bmm_ids.bmm')
  def _compute_en_bmm(self):
    for rec in self:
      rec.en_bmm = sum(rec.en_bmm_ids.mapped('bmm'))

  @api.constrains('en_bmm_ids')
  def _constrains_en_bmm(self):
    if any(rec.en_bmm <= 0 for rec in self):
      raise exceptions.ValidationError('Bạn cần phải nhập BMM cho dự án')

  en_response_rate = fields.Float(string='Cam kết tỉ lệ phản hồi', default=0)
  en_processing_rate = fields.Float(string='Cam kết tỉ lệ xử lý', default=0)
  en_code = fields.Char(string='Mã dự án', required=True)

  @api.constrains('en_code')
  def _en_constrains_en_code(self):
    for rec in self:
      if rec.en_code and self.sudo().with_context(
          active_test=False).search_count([('en_code', '=', rec.en_code)]) > 1:
        raise exceptions.ValidationError(
            f' “Mã dự án” của dự án đang thao tác trùng với các bản ghi khác')
      if ' ' in rec.en_code:
        raise exceptions.ValidationError(
            f'Mã dự án không thể chứa khoảng trắng!')

  en_department_id = fields.Many2one(string='Trung tâm',
                                     comodel_name='hr.department',
                                     required=False,
                                     domain="[('block_id', '=?', en_block_id)]")
  en_project_type_id = fields.Many2one(string='Loại dự án',
                                       comodel_name='en.project.type',
                                       required=True)
  en_list_project_id = fields.Many2one(string='Danh mục dự án',
                                       comodel_name='en.list.project',
                                       required=True)
  en_project_model_id = fields.Many2one(string='Mô hình thực hiện dự án',
                                        comodel_name='en.project.model',
                                        required=True)

  en_resource_ids = fields.One2many(string='Kế hoạch nguồn lực',
                                    comodel_name='en.resource.planning',
                                    inverse_name='project_id')
  en_resource_count = fields.Integer(string='Kế hoạch nguồn lực',
                                     compute_sudo=True,
                                     compute='_compute_en_resource_count')
  en_resource_id = fields.Many2one(string='Kế hoạch nguồn lực',
                                   comodel_name='en.resource.planning',
                                   store=True, compute_sudo=True,
                                   compute='_compute_en_resource_count')
  is_presale = fields.Boolean(related='en_project_type_id.is_presale',
                              store=True)

  @api.constrains('en_department_id', 'en_project_type_id')
  def check_non_presale_project(self):
    if not self.en_project_type_id.is_presale and not self.en_department_id:
      raise UserError('Thiếu giá trị cho trường bắt buộc: Trung tâm')

  @api.onchange('en_area_id')
  def onchange_en_area_id(self):
    # if self.en_project_implementation_id != self.en_area_id.en_project_implementation_id:
    #     self.en_project_implementation_id = self.en_area_id.en_project_implementation_id
    if self.en_block_id.area_id != self.en_area_id:
      self.en_block_id = False

  # @api.onchange('en_project_manager_id')
  # def onchange_en_project_manager_id(self):
  #     self.en_project_block_id = self.en_project_manager_id

  @api.onchange('en_block_id')
  def onchange_en_block_id(self):
    if self.en_department_id.block_id != self.en_block_id:
      self.en_department_id = False
      self.en_project_implementation_id = self.en_block_id.en_project_implementation_id

  @api.onchange('en_department_id')
  def onchange_en_department_id(self):
    if self.en_project_manager_id != self.en_department_id.en_project_manager_id:
      self.en_project_manager_id = self.en_department_id.en_project_manager_id
    self.en_project_block_id = self.en_department_id.sudo().manager_id.user_id.id

  @api.depends('en_resource_ids', 'en_resource_ids.state')
  def _compute_en_resource_count(self):
    for rec in self:
      rec.en_resource_count = len(rec.en_resource_ids)
      en_resource_id = self.env['en.resource.planning']
      for resource in rec.en_resource_ids:
        if resource.state != 'approved':
          continue
        en_resource_id = resource
        break
      rec.en_resource_id = en_resource_id

  def to_resource(self):
    return self.open_form_or_tree_view('ngsd_base.resource_planning_act', False,
                                       self.en_resource_ids,
                                       {'default_project_id': self.id})

  en_project_stage_ids = fields.One2many(string='Giai đoạn dự án',
                                         comodel_name='en.project.stage',
                                         inverse_name='project_id')
  en_workpackage_ids = fields.One2many(string='Gói công việc',
                                       comodel_name='en.workpackage',
                                       inverse_name='project_id')
  en_document_ids = fields.One2many(string='Sản phẩm bàn giao',
                                    comodel_name='en.project.document',
                                    inverse_name='project_id')
  en_document_count = fields.Integer(string='Sản phẩm bàn giao',
                                     compute_sudo=True,
                                     compute='_compute_en_document_count')

  @api.depends('en_document_ids')
  def _compute_en_document_count(self):
    for rec in self:
      rec.en_document_count = len(rec.en_document_ids)

  def to_project_document(self):
    action = self.env.ref('ngsd_base.project_document_act').sudo().read()[0]
    action.update({
      'domain': [('project_id', '=', self.id)],
      'context': {'default_project_id': self.id},
      'view_mode': 'tree,form',
    })
    return action

  en_wbs_ids = fields.One2many(string='Phiên bản', comodel_name='en.wbs',
                               inverse_name='project_id')
  en_wbs_count = fields.Integer(string='WBS', compute_sudo=True,
                                compute='_compute_en_wbs_count')

  @api.depends('en_wbs_ids')
  def _compute_en_wbs_count(self):
    for rec in self:
      rec.en_wbs_count = len(rec.en_wbs_ids)

  def to_wbs(self):
    return self.open_form_or_tree_view('ngsd_base.wbs_act', False,
                                       self.en_wbs_ids,
                                       {'default_project_id': self.id,
                                        'default_user_id': self.user_id.id})

  en_current_version = fields.Many2one(string='Phiên bản WBS hiện tại',
                                       comodel_name='en.wbs', compute_sudo=True,
                                       compute='_compute_en_current_version',
                                       store=True)

  @api.depends('en_wbs_ids', 'en_wbs_ids.state')
  def _compute_en_current_version(self):
    for rec in self:
      en_current_version = self.env['en.wbs']
      if rec.en_wbs_ids.filtered(lambda x: x.state == 'approved'):
        en_current_version = \
          rec.en_wbs_ids.filtered(lambda x: x.state == 'approved')[-1]
      rec.en_current_version = en_current_version

  en_planned_resource = fields.Float(string='Tổng nguồn lực (MM)',
                                     compute_sudo=True,
                                     compute='_compute_en_planned_resource')
  en_md_resource = fields.Float('Tổng nguồn lực (MD)', compute_sudo=True,
                                compute='_compute_en_md_resource')

  show_import_button = fields.Boolean(default=True, groups='base.group_system',
                                      string='Hiển thị nút import')
  show_import_button_viewer = fields.Boolean(related='show_import_button',
                                             groups=False,
                                             string='Hiển thị nút import')

  @api.depends('en_resource_id')
  def _compute_en_md_resource(self):
    for rec in self:
      rec.en_md_resource = rec.en_resource_id.en_md

  @api.depends('en_resource_id')
  def _compute_en_planned_resource(self):
    for rec in self:
      rec.en_planned_resource = rec.en_resource_id.resource_total

  en_response_rate_ids = fields.One2many('en.response.rate', 'project_id',
                                         string='Cam kết tỉ lệ phản hồi')
  en_processing_rate_ids = fields.One2many('en.processing.rate', 'project_id',
                                           string='Cam kết tỉ lệ xử lý')

  def import_wbs(self):
    if self.en_wbs_ids.filtered(lambda w: w.state in ['draft', 'awaiting']):
      raise UserError(
          'Không thể tạo nhiều wbs chưa được duyệt, vui lòng kiểm tra lại.')
    return self.env['ir.actions.act_window']._for_xml_id(
        'ngsd_base.form_view_import_wbs_popup_act')

  def import_en_resource_planning_line(self):
    if self.en_resource_ids.filtered(
        lambda w: w.state in ['draft', 'to_approve']):
      raise UserError(
          'Không thể tạo nhiều KHNL chưa được duyệt, vui lòng kiểm tra lại.')
    action = self.env['ir.actions.client']._for_xml_id(
        'ngsd_base.action_en_resource_planning_line_import')
    action['params']['res_id'] = self.id
    return action

  allow_subtasks = fields.Boolean(default=False)
  allow_task_dependencies = fields.Boolean(default=False)

  en_work_plans_ids = fields.One2many(
      string='Công việc hoàn thành & Kế hoạch tiếp theo',
      comodel_name='en.work.plans', inverse_name='project_id')
  en_work_plans_count = fields.Integer(string='Cập nhật báo cáo tuần',
                                       compute_sudo=True,
                                       compute='_compute_en_work_plans_count')

  en_qa_evaluate_ids = fields.One2many('qa.evaluate', 'project_id',
                                       'QA đánh giá trạng thái')
  en_qa_survey_ids = fields.One2many('qa.survey', 'project_id', 'Survey')
  en_resource_project_ids = fields.One2many('resource.project', 'project_id',
                                            'Danh sách nhân sự', store=True)
  customer_resource_calendar_id = fields.Many2one('resource.calendar',
                                                  'Thời gian làm việc của khách hàng')
  en_history_resource_ids = fields.One2many('history.resource', 'project_id',
                                            'Lịch sử nguồn lực cũ')
  en_quality_control_ids = fields.One2many('en.quality.control', 'project_id',
                                           'Kiểm soát chất lượng',
                                           groups="ngsd_base.group_qam,ngsd_base.group_qal,ngsd_base.group_pm,ngsd_base.group_gdkndu")
  is_pm_project = fields.Boolean('PM Dự án', compute='_compute_pm_project')

  en_project_vicepm_id = fields.Many2one('res.users', 'Vice PM (old)')
  en_project_vicepm_ids = fields.Many2many('res.users',
                                           relattion="project_project_en_project_vicepm_rel",
                                           string='Vice PM')

  def _compute_pm_project(self):
    for rec in self:
      rec.is_pm_project = False
      if rec.en_project_qa_id.id == self.env.uid and rec.en_resource_id and rec.en_resource_id.order_line.filtered(
          lambda x: x.employee_id.user_id.id == self.env.uid):
        rec.is_pm_project = True

  def import_en_quality_control(self):
    if self.en_quality_control_ids.filtered(
        lambda w: w.state in ['draft', 'to_approve']):
      raise UserError(
          'Không thể tạo nhiều KH KSCL chưa được duyệt, vui lòng kiểm tra lại.')
    action = self.env['ir.actions.client']._for_xml_id(
        'ngsd_base.action_quality_control_import')
    action['params']['res_id'] = self.id
    return action

  def import_en_resource_project(self):
    action = self.env['ir.actions.client']._for_xml_id(
        'ngsd_base.action_en_resource_project_import')
    action['params']['res_id'] = self.id
    return action

  @api.depends('en_work_plans_ids')
  def _compute_en_work_plans_count(self):
    for rec in self:
      rec.en_work_plans_count = len(rec.en_work_plans_ids)

  def to_work_plans(self):
    view_id = self.env.ref('ngsd_base.en_work_plans_view_tree').id
    return {
      'name': 'Cập nhật báo cáo tuần',
      'type': 'ir.actions.act_window',
      'view_mode': 'tree',
      'views': [(view_id, 'tree')],
      'res_model': 'en.work.plans',
      'view_id': view_id,
      'target': 'self',
      'domain': [('project_id', '=', self.id)],
      'context': {
        'default_project_id': self.id
      }
    }

  def _convert_resource_to_list_resource(self,
      projects=None):  # hàm để cập nhật nhân viên từ KHNL về DSNS
    if not projects:
      project_ids = self.search([('en_resource_id', '!=', False),
                                 ('en_resource_project_ids', '=', False)]).ids
    else:
      project_ids = projects
    for project in project_ids:
      values = []
      data_create = {}
      try:
        project_id = self.browse(project)
      except:
        continue
      if project_id.en_resource_project_ids: continue
      for resource in project_id.en_resource_id.order_line:
        if not resource.employee_id: continue
        employee_id = resource.employee_id.id
        if resource.employee_id.departure_date and resource.date_start and project_id.date_start and (
            project_id.date_start >= resource.employee_id.departure_date or (
            resource.employee_id.departure_date >= resource.date_start and resource.employee_id.departure_date <= resource.date_end) or resource.employee_id.departure_date <= resource.date_start): continue
        if resource.date_end and resource.date_start and resource.employee_id.en_day_layoff_from and resource.employee_id.en_day_layoff_to and (
            (
                resource.employee_id.en_day_layoff_from >= resource.date_start and resource.employee_id.en_day_layoff_from <= resource.date_end) or (
                resource.employee_id.en_day_layoff_to >= resource.date_start and resource.employee_id.en_day_layoff_to <= resource.date_end)): continue
        type_id = resource.type_id.id if resource.type_id else False
        role_id = resource.role_id.id if resource.role_id else False
        en_job_position_id = resource.job_position_id.id if resource.job_position_id else False
        date_start = resource.date_start if resource.date_start and project_id.date_start and resource.date_start >= project_id.date_start else project_id.date_start
        date_end = resource.date_end if resource.date_end and project_id.date and resource.date_end <= project_id.date else project_id.date
        if employee_id not in data_create:
          data_create[employee_id] = {
            'employee_id': employee_id,
            'type_id': type_id,
            'role_ids': [role_id] if role_id else [],
            'en_job_position_ids': [
              en_job_position_id] if en_job_position_id else [],
            'date_start': date_start,
            'date_end': date_end,
            'project_id': project
          }
        else:
          if role_id and role_id not in data_create[employee_id]['role_ids']:
            data_create[employee_id]['role_ids'] = data_create[employee_id][
                                                     'role_ids'] + [role_id]
          if en_job_position_id and en_job_position_id not in \
              data_create[employee_id]['en_job_position_ids']:
            data_create[employee_id]['en_job_position_ids'] = \
              data_create[employee_id]['en_job_position_ids'] + [
                en_job_position_id]
          if date_start < data_create[employee_id]['date_start']:
            data_create[employee_id]['date_start'] = date_start
          if date_end > data_create[employee_id]['date_end']:
            data_create[employee_id]['date_end'] = date_end
      for data in data_create.values():
        values.append(data)
      if values:
        self.env['resource.project'].sudo().create(values)

  def message_subscribe(self, partner_ids=None, subtype_ids=None):
    """
        Subscribe to all existing active tasks when subscribing to a project
        """
    res = super(ProjectProject, self.sudo()).message_subscribe(
        partner_ids=partner_ids, subtype_ids=subtype_ids)

    return res

  @api.model
  def fields_get(self, allfields=None, attributes=None):
    res = super().fields_get(allfields, attributes)
    if attributes and not 'readonly' in attributes:
      return res
    for fname in res:
      # Check if 'readonly' key exists and if the field is readonly
      field_info = res[fname]
      if field_info.get('readonly', False):
        continue
      field_info.update({
        'readonly_domain': "[('en_state', 'in', ['pending', 'complete'])]"
      })
    return res


class ProjectStage(models.Model):
  _name = 'en.project.stage'
  _description = 'Giai đoạn dự án'
  _inherit = ['mail.thread', 'mail.activity.mixin']
  _order = 'seq_id asc'

  def write(self, vals):
    if vals.get('state') == 'ongoing':
      vals['en_real_start_date'] = fields.Datetime.now()
    if vals.get('state') == 'done':
      vals['en_real_end_date'] = fields.Datetime.now()
    return super().write(vals)

  # tạm thời bỏ readonly
  en_real_start_date = fields.Datetime(string='Ngày bắt đầu thực tế',
                                       readonly=False)
  en_real_end_date = fields.Datetime(string='Ngày kết thúc thực tế',
                                     readonly=False)

  def copy(self, default=None):
    new_project_stage_id = super(ProjectStage, self.with_context(
        default_order_line=False)).copy(default)
    project_stage = self.browse(new_project_stage_id.id)
    workpackages = self.env['en.workpackage']
    # We want to copy archived task, but do not propagate an active_test context key
    workpackage_ids = self.env['en.workpackage'].with_context(
        active_test=False).search([('project_stage_id', '=', self.id)],
                                  order='parent_id').ids
    old_to_new_tasks = {}
    all_workpackages = self.env['en.workpackage'].browse(workpackage_ids)
    newest_resource = self.env['en.resource.planning']
    if self._context.get('newest_resource'):
      newest_resource = self.env['en.resource.planning'].browse(
          self._context.get('newest_resource'))
    for workpackage in all_workpackages:
      # preserve task name and stage, normally altered during copy
      defaults = {'wbs_version_old': workpackage.wbs_version.id}

      if workpackage.parent_id:
        # set the parent to the duplicated task
        parent_id = old_to_new_tasks.get(workpackage.parent_id.id, False)
        defaults['parent_id'] = parent_id
        if not parent_id or workpackage.project_stage_id:
          defaults[
            'project_stage_id'] = project_stage.id if workpackage.project_stage_id == self else False
        #     defaults['display_project_id'] = project.id if task.display_project_id == self else False
      elif workpackage.project_stage_id == self:
        defaults['project_stage_id'] = project_stage.id
      if 'type_id' in defaults:
        defaults.pop('type_id')
      ctx = dict(self._context)
      ctx['new_resource'] = newest_resource.id
      if 'type_id' in ctx:
        ctx.pop('type_id')
      new_workpackage = workpackage.with_context(**ctx).copy(defaults)
      # If child are created before parent (ex sub_sub_tasks)
      new_child_ids = [old_to_new_tasks[child.id] for child in
                       workpackage.child_ids if child.id in old_to_new_tasks]
      workpackages.browse(new_child_ids).write(
          {'parent_id': new_workpackage.id})
      old_to_new_tasks[workpackage.id] = new_workpackage.id
      workpackages += new_workpackage
    project_stage.write({'order_line': [(6, 0, workpackages.ids)]})
    return new_project_stage_id

    # new_record = self.copy_data({'version_type': 'plan'})

  origin_code = fields.Char(string='Mã gốc', readonly=True, copy=True)

  @api.model_create_multi
  def create(self, vals_list):
    res = super().create(vals_list)
    for rec in res:
      if not rec.origin_code:
        rec.write({'origin_code': f'P{rec.id}'})
    return res

  wbs_state = fields.Selection(related='wbs_version.state')

  @api.model
  def fields_view_get(self, view_id=None, view_type='form', toolbar=False,
      submenu=False):
    res = super().fields_view_get(view_id=view_id, view_type=view_type,
                                  toolbar=toolbar, submenu=submenu)
    if view_type != 'form':
      return res
    doc = etree.XML(res['arch'])
    for node in doc.xpath(f"//{view_type}"):
      wbs_state = etree.Element('field', attrib={'name': 'wbs_state',
                                                 'modifiers': json.dumps(
                                                     {'column_invisible': True,
                                                      'invisible': True})})
      node.append(wbs_state)
    for node in doc.xpath("//field"):
      if self.env['en.project.stage'].fields_get([node.attrib.get('name')]).get(
          node.attrib.get('name'), {}).get('readonly'): continue
      if node.attrib.get('name') in ['state', 'order_line']: continue
      modifiers = json.loads(node.get("modifiers", "{}"))
      readonly = modifiers.get('readonly', [])
      # readonly_domain = [('wbs_state', '=', 'approved')]
      # if readonly and isinstance(readonly, list):
      #     readonly_domain = Domain.OR([readonly, readonly_domain])
      # elif not readonly and isinstance(readonly, bool):
      #     readonly_domain = readonly
      # modifiers['readonly'] = readonly_domain
      # node.set("modifiers", json.dumps(modifiers)) # tạm thời bỏ readonly
    res['arch'] = etree.tostring(doc, encoding='unicode')
    return res

  wbs_version = fields.Many2one(string='Phiên bản', comodel_name='en.wbs',
                                required=True, ondelete='cascade')
  wbs_version_old = fields.Many2one(string='Phiên bản wbs cũ',
                                    comodel_name='en.wbs', copy=False)
  project_id = fields.Many2one(string='Dự án', comodel_name='project.project',
                               related='wbs_version.project_id')
  name = fields.Char(string='Tên', required=True)
  stage_type_id = fields.Many2one(string='Loại giai đoạn',
                                  comodel_name='en.stage.type', required=True)
  stage_code = fields.Char(string='Mã giai đoạn', readonly=True, copy=False,
                           compute_sudo=True, compute='_compute_stage_code',
                           store=True)
  seq_id = fields.Integer(string='💰', default=lambda self: int(
      self.env['ir.sequence'].next_by_code('seq.id')), copy=False)

  @api.depends("wbs_version.project_stage_ids", "seq_id")
  def _compute_stage_code(self):
    for project in self.mapped("wbs_version"):
      sequence = 1
      stage_ids = project.project_stage_ids
      for line in sorted(stage_ids, key=lambda l: l.seq_id):
        line.stage_code = f"P.{sequence}"
        sequence += 1

  @api.constrains('wbs_version', 'start_date', 'end_date')
  def _en_constrains_en_start_date_message(self):
    date_gt_error = self.filtered(lambda
                                      rec: rec.project_id.date_start and rec.start_date and rec.start_date < rec.project_id.date_start)
    if date_gt_error:
      lst = [f'\t- {s.stage_code}: {s.name}' for s in date_gt_error]
      text = (
          f'Ngày bắt đầu giai đoạn không được nhỏ hơn Ngày bắt đầu dự án. Giai đoạn lỗi gồm:\n' + '\n'.join(
          lst))
      self.env.user.notify_warning(text, 'Cảnh báo')
    date_lt_error = self.filtered(lambda
                                      rec: rec.project_id.date and rec.end_date and rec.end_date > rec.project_id.date)
    if date_lt_error:
      lst = [f'\t- {s.stage_code}: {s.name}' for s in date_lt_error]
      text_1 = (
          f'Ngày kết thúc giai đoạn không được lớn hơn Ngày kết thúc dự án. Giai đoạn lỗi gồm:\n' + '\n'.join(
          lst))
      self.env.user.notify_warning(text_1, 'Cảnh báo')
    date_error = self.filtered(lambda
                                   rec: rec.end_date and rec.start_date and rec.end_date < rec.start_date)
    if date_error:
      lst = [f'\t- {s.stage_code}: {s.name}' for s in date_error]
      text_2 = (
          f'Ngày bắt đầu giai đoạn không được lớn hơn Ngày kết thúc giai đoạn. Giai đoạn lỗi gồm:\n' + '\n'.join(
          lst))
      self.env.user.notify_warning(text_2, 'Cảnh báo')

  def _en_constrains_en_start_date(self):
    date_gt_error = self.filtered(lambda
                                      rec: rec.project_id.date_start and rec.start_date and rec.start_date < rec.project_id.date_start)
    if date_gt_error:
      lst = [f'\t- {s.stage_code}: {s.name}' for s in date_gt_error]
      raise exceptions.ValidationError(
          f'Ngày bắt đầu giai đoạn không được nhỏ hơn Ngày bắt đầu dự án. Giai đoạn lỗi gồm:\n' + '\n'.join(
              lst))
    date_lt_error = self.filtered(lambda
                                      rec: rec.project_id.date and rec.end_date and rec.end_date > rec.project_id.date)
    if date_lt_error:
      lst = [f'\t- {s.stage_code}: {s.name}' for s in date_lt_error]
      raise exceptions.ValidationError(
          f'Ngày kết thúc giai đoạn không được lớn hơn Ngày kết thúc dự án. Giai đoạn lỗi gồm:\n' + '\n'.join(
              lst))
    date_error = self.filtered(lambda
                                   rec: rec.end_date and rec.start_date and rec.end_date < rec.start_date)
    if date_error:
      lst = [f'\t- {s.stage_code}: {s.name}' for s in date_error]
      raise exceptions.ValidationError(
          f'Ngày bắt đầu giai đoạn không được lớn hơn Ngày kết thúc giai đoạn. Giai đoạn lỗi gồm:\n' + '\n'.join(
              lst))

  start_date = fields.Date(string='Ngày bắt đầu', required=True)
  end_date = fields.Date(string='Ngày kết thúc', required=True)

  technical_field_27058 = fields.Float(string='🚑', compute_sudo=True,
                                       compute='_compute_technical_field_27058')

  @api.depends('order_line')
  def _compute_technical_field_27058(self):
    for rec in self:
      technical_field_27058 = 0
      if rec.end_date <= date(2024, 3, 31):
        technical_field_27058 = 1
      elif rec.order_line:
        technical_field_27058 = sum(
            [child.technical_field_27058 * child.technical_field_27058a for
             child in rec.order_line]) / sum(
            rec.order_line.mapped('technical_field_27058a')) if sum(
            rec.order_line.mapped('technical_field_27058a')) else 0
      rec.technical_field_27058 = min(technical_field_27058, 1)

  technical_field_27058a = fields.Float(string='🚑', compute_sudo=True,
                                        compute='_compute_technical_field_27058a')

  @api.depends('order_line')
  def _compute_technical_field_27058a(self):
    for rec in self:
      rec.technical_field_27058a = sum(self.env['project.task'].search(
          [('en_task_position', 'child_of', rec.order_line.ids)]).mapped(
          'planned_hours'))

  en_approver_id = fields.Many2one(string='Người xem xét',
                                   comodel_name='res.users', compute_sudo=True,
                                   compute='_compute_en_approver_id',
                                   store=True, readonly=False)

  @api.depends('wbs_version')
  def _compute_en_approver_id(self):
    for rec in self:
      rec.en_approver_id = rec.project_id.user_id

  a_ok = fields.Boolean(string='🚑', compute='_compute_en_ok')
  b_ok = fields.Boolean(string='🚑', compute='_compute_en_ok')
  c_ok = fields.Boolean(string='🚑', compute='_compute_en_ok')
  d_ok = fields.Boolean(string='🚑', compute='_compute_en_ok')
  e_ok = fields.Boolean(string='🚑', compute='_compute_en_ok')

  @api.depends_context('uid')
  @api.depends('order_line', 'order_line.child_ids', 'order_line.task_ids',
               'en_approver_id')
  def _compute_en_ok(self):
    for rec in self:
      task_ids = self.env['project.task'].search(
          [('en_task_position', 'child_of', rec.order_line.ids)])
      rec.a_ok = task_ids and all(
          task.stage_id.en_mark in ['b'] for task in task_ids)
      rec.b_ok = task_ids and all(
          task.stage_id.en_mark in ['b', 'g'] for task in task_ids)
      rec.c_ok = task_ids and (
          all(task.stage_id.en_mark in ['e'] for task in task_ids) or (
          any(task.stage_id.en_mark in ['e'] for task in task_ids) and all(
          task.stage_id.en_mark in ['g'] for task in task_ids)))
      rec.d_ok = task_ids and any(task.stage_id.en_mark in ['f'] for task in
                                  task_ids) and self.env.user == rec.en_approver_id
      rec.e_ok = task_ids and all(
          task.stage_id.en_mark in ['b', 'g'] for task in
          task_ids) and self.env.user == rec.en_approver_id

  def button_en_a(self):
    if not self.a_ok: return
    self.write({'state': 'cancel'})

  def button_en_b(self):
    if not self.b_ok: return
    if self.en_approver_id: self.send_notify('Bạn có thông tin cần xem xét',
                                             self.en_approver_id)
    self.write({'state': 'review'})

  def button_en_c(self):
    if not self.c_ok: return
    self.write({'state': 'delayed'})

  def button_en_d(self):
    if not self.d_ok: return
    self.write({'state': 'redone'})

  def button_en_e(self):
    if not self.e_ok: return
    self.write({'state': 'done'})

  state = fields.Selection(string='Trạng thái',
                           selection=[('draft', 'Chờ thực hiện'),
                                      ('ongoing', 'Đang thực hiện'),
                                      ('review', 'Chờ xem xét'),
                                      ('delayed', 'Bị trì hoãn'),
                                      ('redone', 'Làm lại'),
                                      ('done', 'Đã hoàn thành'),
                                      ('cancel', 'Hủy bỏ')], required=True,
                           default='draft', copy=True, readonly=True)
  project_milestone = fields.Boolean(string='Mốc dự án', default=False)
  payment_milestone = fields.Boolean(string='Mốc thanh toán', default=False)
  order_line = fields.One2many(string='Gói công việc',
                               comodel_name='en.workpackage',
                               inverse_name='project_stage_id')
  workpackage_count = fields.Integer(string='Gói công việc', compute_sudo=True,
                                     compute='_compute_workpackage_count')

  @api.depends('order_line')
  def _compute_workpackage_count(self):
    for rec in self:
      rec.workpackage_count = len(rec.order_line)

  def to_workpackage(self):
    return self.open_form_or_tree_view('ngsd_base.workpackage_act', False,
                                       self.order_line, {
                                         'create': self.wbs_state not in READONLY_STATES.keys(),
                                         'edit': self.wbs_state not in READONLY_STATES.keys(),
                                         'delete': self.wbs_state not in READONLY_STATES.keys(),
                                         'default_project_stage_id': self.id,
                                         'default_user_id': self.wbs_version.user_id.id,
                                         'default_date_start': self.start_date,
                                         'default_date_end': self.end_date})

  @api.model
  def _name_search(self, name, args=None, operator='ilike', limit=100,
      name_get_uid=None):
    if self._context.get('import_file') and self._context.get(
        'import_order_line') == 'wbs_version.id' and self._context.get(
        'relation_id'):
      args = args or []
      args = [('wbs_version', '=', self._context.get('relation_id'))] + args
    res = super()._name_search(name, args, operator, limit, name_get_uid)
    return res


class ProjectDocument(models.Model):
  _name = 'en.project.document'
  _description = 'Sản phẩm bàn giao'
  _inherit = ['mail.thread', 'mail.activity.mixin']

  create_uid = fields.Many2one(comodel_name='res.users', readonly=False)
  user_id = fields.Many2one(comodel_name='res.users',
                            string='Người tạo sản phẩm')
  doc_type = fields.Selection(string='Loại sản phẩm',
                              selection=[('pdf', 'PDF'), ('doc', 'DOC'),
                                         ('docx', 'DOCX'), ('excel', 'EXCEL'),
                                         ('hard', 'Bản cứng'),
                                         ('jpe', 'JPE')])
  doc_version = fields.Selection(string='Kiểu sản phẩm',
                                 selection=[('soft', 'Bản mềm'),
                                            ('hard', 'Bản cứng')])
  doc_area = fields.Char(string='Phạm vi thực hiện', default='Dự án')
  real_ho_date = fields.Date(string='Ngày bàn giao thực tế')
  description = fields.Text(string='Mô tả')
  external_assesser = fields.Char(string='Người thẩm định bên nhận')
  out_assess = fields.Boolean(string='Thẩm định bên ngoài hệ thống')
  external_approver = fields.Char(string='Người phê duyệt bên nhận')
  out_approve = fields.Boolean(string='Phê duyệt bên ngoài hệ thống')
  internal_approver_id = fields.Many2one(string='Người phê duyệt',
                                         comodel_name='res.users',
                                         domain="[('employee_id','!=',False)]")
  internal_examiner_id = fields.Many2one(string='Người xem xét',
                                         comodel_name='res.users',
                                         domain="[('employee_id','!=',False)]")
  state = fields.Selection(string='Trạng thái',
                           selection=[('new', 'Chưa bàn giao'),
                                      ('done', 'Đã bàn giao'),
                                      ('cancelled', 'Hủy bàn giao')],
                           default='new', readonly=False, copy=True,
                           required=True)

  project_id = fields.Many2one(string='Dự án', comodel_name='project.project',
                               required=True, store=True, readonly=False,
                               ondelete='cascade')
  en_payment_milestone = fields.Boolean('Mốc thanh toán')
  en_project_milestone = fields.Boolean('Mốc dự án')
  en_state = fields.Many2one('en.stage.type', 'Loại giai đoạn')

  @api.depends('workpackage_id', 'workpackage_id.project_id')
  def _compute_project_id(self):
    for rec in self:
      project_id = rec.project_id
      if rec.workpackage_id:
        project_id = rec.workpackage_id.project_id
      rec.project_id = project_id

  workpackage_id = fields.Many2one(string='Gói công việc',
                                   comodel_name='en.workpackage')
  name = fields.Char(string='Tên sản phẩm', required=True)
  handover_date = fields.Date(string='Hoàn thành dự kiến', required=1)

  data_attachment = fields.Binary(string="Đính kèm")
  file_name = fields.Char("Tên tệp đính kèm")
  product_url = fields.Char("Link sản phẩm")

  @api.model
  def default_get(self, fields):
    vals = super(ProjectDocument, self).default_get(fields)
    if 'user_id' in fields and not 'default_user_id' in self._context and not vals.get(
        'user_id'):
      vals['user_id'] = self.env.user.id
    return vals

  def write(self, vals):
    if vals.get("state") == "done" and not self.real_ho_date:
      vals['real_ho_date'] = fields.Datetime.now()
    return super(ProjectDocument, self).write(vals)


class Workpackage(models.Model):
  _name = 'en.workpackage'
  _description = 'Gói công việc'
  _parent_store = True
  _inherit = ['mail.thread', 'mail.activity.mixin']
  _order = 'parent_id desc,seq_id asc'

  def write(self, vals):
    if vals.get('state') == 'ongoing':
      vals['en_real_start_date'] = fields.Datetime.now()
    if vals.get('state') == 'done':
      vals['en_real_end_date'] = fields.Datetime.now()
    return super().write(vals)

  # tạm thời bỏ readonly
  en_real_start_date = fields.Datetime(string='Ngày bắt đầu thực tế',
                                       readonly=False)
  en_real_end_date = fields.Datetime(string='Ngày kết thúc thực tế',
                                     readonly=False)

  def copy(self, default=None):
    workpackage = super().copy(default)
    tasks = self.env['project.task']
    # We want to copy archived task, but do not propagate an active_test context key
    task_ids = self.env['project.task'].with_context(active_test=False).search(
        [('en_task_position', '=', self.id)], order='parent_id').ids
    old_to_new_tasks = {}
    all_tasks = self.env['project.task'].browse(task_ids)
    for task in all_tasks:
      # if task.date_deadline and task.date_deadline < fields.Date.today(): continue
      # preserve task name and stage, normally altered during copy
      defaults = {'name': task.name, 'stage_id': task.stage_id.id,
                  'planned_hours': task.planned_hours, 'timesheet_ids': False,
                  'en_wbs_old_id': task.en_wbs_id.id}
      en_start_date = task.en_start_date
      if en_start_date < fields.Date.today():
        en_start_date = fields.Date.today()
      defaults['en_start_date'] = en_start_date
      if task.parent_id:
        # set the parent to the duplicated task
        parent_id = old_to_new_tasks.get(task.parent_id.id, False)
        defaults['parent_id'] = parent_id
        if not parent_id or task.en_task_position:
          defaults[
            'en_task_position'] = workpackage.id if task.en_task_position == self else False
        #     defaults['display_project_id'] = project.id if task.display_project_id == self else False
      elif task.en_task_position == self:
        defaults['en_task_position'] = workpackage.id
      #     defaults['display_project_id'] = project.id
      en_handler = task.en_handler.id
      data_defaults = [
        {'en_handler': en_handler, 'en_task_code': task.en_task_code,
         'related_task_id': task.id, 'en_start_date': task.en_start_date,
         'date_deadline': task.date_deadline}]

      for data_default in data_defaults:
        data_write = defaults.copy()
        data_write.update(data_default)
        new_task = task.with_context(mail_auto_subscribe_no_notify=True).copy(
            data_write)
        tasks += new_task
    # project.write({'task_ids': [(6, 0, tasks.ids)]})
    return workpackage

  def compare_date_task_and_resource(self, resource, user, start_date,
      end_date):
    return [(start_date, end_date)]
    # all_current_range = []
    # current_range = []
    # for date_check in daterange(start_date, end_date):
    #     resource_line = resource.order_line.filtered(lambda x: x.employee_id == user.employee_id and x.date_start <= date_check <= x.date_end)
    #     if resource_line:
    #         current_range.append(date_check)
    #     elif current_range:
    #         all_current_range.append(current_range)
    #         current_range = []
    # if current_range:
    #     all_current_range.append(current_range)
    # return [(min(x), max(x)) for x in all_current_range]

  technical_field_27536 = fields.Many2many(string='🐧', comodel_name='res.users',
                                           compute_sudo=True,
                                           compute='_compute_technical_field_27536')

  @api.depends('project_stage_id', 'parent_id')
  def _compute_technical_field_27536(self):
    for rec in self:
      rec.technical_field_27536 = rec.project_id.en_resource_project_ids.mapped(
          'employee_id.user_id')

  en_approver_id = fields.Many2one(string='Người xem xét',
                                   comodel_name='res.users', compute_sudo=True,
                                   compute='_compute_en_approver_id',
                                   store=True, readonly=False)

  @api.depends('wbs_version')
  def _compute_en_approver_id(self):
    for rec in self:
      rec.en_approver_id = rec.project_id.user_id

  a_ok = fields.Boolean(string='🚑', compute='_compute_en_ok')
  b_ok = fields.Boolean(string='🚑', compute='_compute_en_ok')
  c_ok = fields.Boolean(string='🚑', compute='_compute_en_ok')
  d_ok = fields.Boolean(string='🚑', compute='_compute_en_ok')
  e_ok = fields.Boolean(string='🚑', compute='_compute_en_ok')

  @api.depends_context('uid')
  @api.depends('child_ids', 'child_ids.task_ids', 'task_ids', 'en_approver_id')
  def _compute_en_ok(self):
    for rec in self:
      task_ids = self.env['project.task'].search(
          [('en_task_position', 'child_of', rec.ids)])
      rec.a_ok = task_ids and all(
          task.stage_id.en_mark in ['b'] for task in task_ids)
      rec.b_ok = task_ids and all(
          task.stage_id.en_mark in ['b', 'g'] for task in task_ids)
      rec.c_ok = task_ids and (
          all(task.stage_id.en_mark in ['e'] for task in task_ids) or (
          any(task.stage_id.en_mark in ['e'] for task in task_ids) and all(
          task.stage_id.en_mark in ['g'] for task in task_ids)))
      rec.d_ok = task_ids and any(task.stage_id.en_mark in ['f'] for task in
                                  task_ids) and self.env.user == rec.en_approver_id
      rec.e_ok = task_ids and all(
          task.stage_id.en_mark in ['b', 'g'] for task in
          task_ids) and self.env.user == rec.en_approver_id

  def button_en_a(self):
    if not self.a_ok: return
    self.write({'state': 'cancel'})

  def button_en_b(self):
    if not self.b_ok: return
    if self.en_approver_id: self.send_notify('Bạn có thông tin cần xem xét',
                                             self.en_approver_id)
    self.write({'state': 'review'})

  def button_en_c(self):
    if not self.c_ok: return
    self.write({'state': 'delayed'})

  def button_en_d(self):
    if not self.d_ok: return
    self.write({'state': 'redone'})

  def button_en_e(self):
    if not self.e_ok: return
    self.write({'state': 'done'})

  origin_code = fields.Char(string='Mã gốc', readonly=True, copy=True)

  @api.model_create_multi
  def create(self, vals_list):
    res = super().create(vals_list)
    for rec in res:
      if not rec.origin_code:
        rec.write({'origin_code': f'Z{rec.id}'})
    return res

  wbs_state = fields.Selection(related='wbs_version.state')

  @api.model
  def fields_view_get(self, view_id=None, view_type='form', toolbar=False,
      submenu=False):
    res = super().fields_view_get(view_id=view_id, view_type=view_type,
                                  toolbar=toolbar, submenu=submenu)
    if view_type != 'form':
      return res
    doc = etree.XML(res['arch'])
    for node in doc.xpath(f"//{view_type}"):
      wbs_state = etree.Element('field', {'name': 'wbs_state',
                                          'modifiers': json.dumps(
                                              {'column_invisible': True,
                                               'invisible': True})})
      node.append(wbs_state)
    for node in doc.xpath("//field"):
      if self.env['en.workpackage'].fields_get([node.attrib.get('name')]).get(
          node.attrib.get('name'), {}).get('readonly'):
        continue
      if node.attrib.get('name') in ['state']:
        continue
      modifiers = json.loads(node.get("modifiers", "{}"))
      readonly = modifiers.get('readonly', [])
      readonly_domain = [('wbs_state', '!=', 'draft')]
      if readonly and isinstance(readonly, list):
        readonly_domain = Domain.OR([readonly, readonly_domain])
      elif not readonly and isinstance(readonly, bool):
        readonly_domain = readonly
      modifiers['readonly'] = readonly_domain
      node.set("modifiers", json.dumps(modifiers))  # tạm thời bỏ readonly
    res['arch'] = etree.tostring(doc, encoding='unicode')
    return res

  @api.constrains('parent_id')
  def _check_parent_id(self):
    if not self._check_recursion():
      raise ValidationError('You cannot create recursive records.')

  seq_id = fields.Integer(string='💰', default=lambda self: int(
      self.env['ir.sequence'].next_by_code('seq.id')), copy=False)
  state = fields.Selection(string='Trạng thái',
                           selection=[('draft', 'Chờ thực hiện'),
                                      ('ongoing', 'Đang thực hiện'),
                                      ('review', 'Chờ xem xét'),
                                      ('delayed', 'Bị trì hoãn'),
                                      ('redone', 'Làm lại'),
                                      ('done', 'Đã hoàn thành'),
                                      ('cancel', 'Hủy bỏ')], required=True,
                           default='draft', readonly=True, copy=True)
  wp_code = fields.Char(string='Mã gói việc', readonly=True, copy=False,
                        compute_sudo=True, compute='_compute_wp_code',
                        store=True)

  @api.depends('project_stage_id.order_line', 'parent_id.child_ids', "seq_id")
  def _compute_wp_code(self):
    for workpackage in self.filtered(lambda x: x.parent_id).mapped("parent_id"):
      sequence = 1
      wps = workpackage.child_ids.filtered(lambda x: x.parent_id)
      for line in sorted(wps, key=lambda l: l.seq_id):
        line.wp_code = f"Z{sequence}"
        sequence += 1
    for project in self.filtered(lambda x: not x.parent_id).mapped(
        "project_stage_id"):
      sequence = 1
      wps = project.order_line.filtered(lambda x: not x.parent_id)
      for line in sorted(wps, key=lambda l: l.seq_id):
        line.wp_code = f"W.{sequence}"
        sequence += 1

  name = fields.Char(string='Tên gói việc', required=True)
  project_id = fields.Many2one(string='Dự án', comodel_name='project.project',
                               related='wbs_version.project_id')
  wbs_version = fields.Many2one(string='Phiên bản', comodel_name='en.wbs',
                                recursive=True, compute_sudo=True,
                                compute='_compute_wbs_version', store=True)
  wbs_version_old = fields.Many2one(string='Phiên bản wbs cũ',
                                    comodel_name='en.wbs', copy=False)

  @api.depends('project_stage_id.wbs_version', 'parent_id.wbs_version',
               'project_stage_id', 'parent_id')
  def _compute_wbs_version(self):
    for rec in self:
      wbs_version = rec.wbs_version
      if rec.parent_id:
        wbs_version = rec.parent_id.wbs_version
      elif rec.project_stage_id:
        wbs_version = rec.project_stage_id.wbs_version
      rec.wbs_version = wbs_version

  project_stage_id = fields.Many2one(string='Giai đoạn dự án',
                                     comodel_name='en.project.stage',
                                     recursive=True, required=True,
                                     compute_sudo=True,
                                     compute='_compute_project_stage_id',
                                     readonly=False, store=True,
                                     ondelete='cascade')

  @api.depends('parent_id.project_stage_id', 'parent_id')
  def _compute_project_stage_id(self):
    for rec in self:
      project_stage_id = rec.project_stage_id
      if rec.parent_id:
        project_stage_id = rec.parent_id.project_stage_id
      rec.project_stage_id = project_stage_id

  user_id = fields.Many2one(string='Người chịu trách nhiệm',
                            comodel_name='res.users', required=True)
  date_start = fields.Date(string='Ngày bắt đầu', required=True)
  date_end = fields.Date(string='Ngày kết thúc', required=True)
  pj_milestone = fields.Boolean(string='Mốc dự án', default=False)
  handover_doc = fields.Boolean(string='Sản phẩm bàn giao', default=False)
  child_ids = fields.One2many(string="Gói việc con",
                              comodel_name='en.workpackage',
                              inverse_name='parent_id')
  child_count = fields.Integer(string="Gói việc con", compute_sudo=True,
                               compute='_compute_child_count')
  en_small_package_ids = fields.Many2many('en.workpackage',
                                          compute='_compute_small_package',
                                          string="Gói việc con")

  @api.depends('child_ids')
  def _compute_small_package(self):
    for rec in self:
      rec.en_small_package_ids = False
      for package in rec.child_ids:
        rec.en_small_package_ids = [(4, package.id)]

  @api.depends('child_ids')
  def _compute_child_count(self):
    for rec in self:
      rec.child_count = len(rec.child_ids)

  def to_child(self):
    return self.open_form_or_tree_view('ngsd_base.workpackage_act', False,
                                       self.child_ids, {
                                         'create': self.wbs_state not in READONLY_STATES.keys(),
                                         'edit': self.wbs_state not in READONLY_STATES.keys(),
                                         'delete': self.wbs_state not in READONLY_STATES.keys(),
                                         'default_parent_id': self.id,
                                         'default_user_id': self.user_id.id,
                                         'default_date_start': self.date_start,
                                         'default_date_end': self.date_end})

  parent_id = fields.Many2one(string="Gói việc cha",
                              comodel_name='en.workpackage', index=True)
  parent_path = fields.Char(index=True)
  parent_name = fields.Char()

  task_ids = fields.One2many(copy=False, string='Công việc',
                             comodel_name='project.task',
                             inverse_name='en_task_position')
  task_count = fields.Integer(string="Công việc", compute_sudo=True,
                              compute='_compute_task_count')

  @api.depends('task_ids')
  def _compute_task_count(self):
    for rec in self:
      rec.task_count = len(rec.task_ids)

  def to_task(self):
    return self.open_form_or_tree_view('ngsd_base.project_task_act', False,
                                       self.task_ids, {
                                         'create': self.wbs_state not in READONLY_STATES.keys(),
                                         'delete': self.wbs_state not in READONLY_STATES.keys(),
                                         'default_en_start_date': self.date_start,
                                         'default_date_deadline': self.date_end,
                                         'default_project_id': self.project_id.id,
                                         'default_en_task_position': self.id},
                                       'Công việc')

  technical_field_27058 = fields.Float(string='🚑', compute_sudo=True,
                                       compute='_compute_technical_field_27058',
                                       recursive=True,
                                       help='% Hoàn thành kế hoạch')

  @api.depends('task_ids', 'child_ids')
  def _compute_technical_field_27058(self):
    for rec in self:
      technical_field_27058 = 0
      if rec.date_end <= date(2024, 3, 31):
        technical_field_27058 = 1
      elif rec.child_ids:
        technical_field_27058 = sum(
            [child.technical_field_27058 * child.technical_field_27058a for
             child in rec.child_ids]) / sum(
            rec.child_ids.mapped('technical_field_27058a')) if sum(
            rec.child_ids.mapped('technical_field_27058a')) else 0
      else:
        task_ids = rec.task_ids.filtered(lambda x: x.stage_id.en_mark != 'b')
        technical_field_27058 = sum(
            [task.technical_field_27058 * task.planned_hours for task in
             task_ids]) / sum(task_ids.mapped('planned_hours')) if sum(
            task_ids.mapped('planned_hours')) else 0
      rec.technical_field_27058 = min(technical_field_27058, 1)

  technical_field_27058a = fields.Float(string='🚑', compute_sudo=True,
                                        compute='_compute_technical_field_27058a',
                                        recursive=True, help='Tổng giờ thực tế')

  @api.depends('child_ids', 'task_ids')
  def _compute_technical_field_27058a(self):
    for rec in self:
      if rec.date_end and rec.date_start and rec.date_end <= date(2024, 3, 31):
        technical_field_27058a = self.env[
          'en.technical.model'].convert_daterange_to_hours(
            rec.user_id.employee_id, rec.date_start,
            rec.date_end) if rec.user_id.employee_id else 0
      elif rec.child_ids:
        technical_field_27058a = sum(
            rec.child_ids.mapped('technical_field_27058a'))
      else:
        technical_field_27058a = sum(
            rec.task_ids.filtered(lambda x: x.stage_id.en_mark != 'b').mapped(
                'planned_hours'))

      rec.technical_field_27058a = technical_field_27058a

  effective_hours = fields.Float(string='🚑', compute_sudo=True,
                                 compute='_compute_effective_hours',
                                 recursive=True, help='Tổng giờ thực tế')

  @api.depends('child_ids', 'task_ids')
  def _compute_effective_hours(self):
    for rec in self:
      if rec.date_end and rec.date_start and rec.date_end <= date(2024, 3, 31):
        effective_hours = self.env[
          'en.technical.model'].convert_daterange_to_hours(
            rec.user_id.employee_id, rec.date_start,
            rec.date_end) if rec.user_id.employee_id else 0
      elif rec.child_ids:
        effective_hours = sum(rec.child_ids.mapped('effective_hours'))
      else:
        effective_hours = sum(
            rec.task_ids.filtered(lambda x: x.stage_id.en_mark != 'b').mapped(
                'effective_hours'))

      rec.effective_hours = effective_hours

  en_progress = fields.Float(string='% Hoàn thành thực tế', compute_sudo=True,
                             compute='_compute_en_progress', recursive=True)

  @api.depends('child_ids', 'task_ids')
  def _compute_en_progress(self):
    for rec in self:
      if rec.date_end <= date(2024, 3, 31):
        en_progress = 1
      elif rec.child_ids:
        en_progress = sum(
            [child.en_progress * child.technical_field_27058a for child in
             rec.child_ids]) / sum(
            rec.child_ids.mapped('technical_field_27058a')) if sum(
            rec.child_ids.mapped('technical_field_27058a')) else 0
        # en_progress = sum(rec.child_ids.mapped('en_progress')) / len(rec.child_ids)
      else:
        task_ids = rec.task_ids.filtered(lambda x: x.stage_id.en_mark != 'b')
        en_progress = sum(
            [task.en_progress * task.planned_hours for task in task_ids]) / sum(
            task_ids.mapped('planned_hours')) if sum(
            task_ids.mapped('planned_hours')) else 0
      rec.en_progress = min(en_progress, 1)

  document_ids = fields.One2many(copy=True, string='Sản phẩm bàn giao',
                                 comodel_name='en.project.document',
                                 inverse_name='workpackage_id')

  @api.constrains('date_start', 'date_end', 'project_stage_id', 'parent_id')
  def _constrains_date_1(self):
    date_stage_start_error = self.filtered(lambda
                                               rec: not rec.parent_id and rec.date_start and rec.project_stage_id.start_date and rec.date_start < rec.project_stage_id.start_date)
    if date_stage_start_error:
      lst = [
        f'\t- {w.wp_code}: {w.name} - {w.project_stage_id.stage_code}: {w.project_stage_id.name}'
        for w in date_stage_start_error]
      text = (
          f"Ngày bắt đầu gói việc không được nhỏ hơn ngày bắt đầu của giai đoạn. Cặp gói việc - giai đoạn lỗi gồm:\n" + '\n'.join(
          lst))
      self.env.user.notify_warning(text, 'Cảnh báo')
    date_stage_end_error = self.filtered(lambda
                                             rec: not rec.parent_id and rec.date_end and rec.project_stage_id.end_date and rec.date_end > rec.project_stage_id.end_date)
    if date_stage_end_error:
      lst = [
        f'\t- {w.wp_code}: {w.name} - {w.project_stage_id.stage_code}: {w.project_stage_id.name}'
        for w in date_stage_end_error]
      text_1 = (
          f"Ngày kết thúc gói việc không được lớn hơn ngày kết thúc giai đoạn. Cặp gói việc - giai đoạn lỗi gồm:\n" + '\n'.join(
          lst))
      self.env.user.notify_warning(text_1, 'Cảnh báo')
    date_lt_parent_error = self.filtered(lambda
                                             rec: rec.parent_id and rec.date_start and rec.parent_id.date_start and rec.date_start < rec.parent_id.date_start)
    if date_lt_parent_error:
      lst = [
        f'\t- {w.wp_code}: {w.name} - {w.parent_id.wp_code}: {w.parent_id.name}'
        for w in date_lt_parent_error]
      text_2 = (
          f"Ngày bắt đầu gói việc con không được nhỏ hơn ngày bắt đầu gói việc cha của nó. Cặp gói việc  lỗi gồm:\n" + '\n'.join(
          lst))
      self.env.user.notify_warning(text_2, 'Cảnh báo')
    date_gt_error = self.filtered(lambda
                                      rec: rec.date_start and rec.date_end and rec.project_stage_id and not (
        rec.date_start <= rec.date_end <= rec.project_stage_id.end_date))
    if date_gt_error:
      lst = [f'\t- {w.wp_code}: {w.name}' for w in date_gt_error]
      text_3 = (
          f"Ngày bắt đầu gói việc không được lớn hơn ngày kết thúc gói việc. Vị trí gói việc lỗi gồm:\n" + '\n'.join(
          lst))
      self.env.user.notify_warning(text_3, 'Cảnh báo')

  def _constrains_date(self):
    date_stage_start_error = self.filtered(lambda
                                               rec: not rec.parent_id and rec.date_start and rec.project_stage_id.start_date and rec.date_start < rec.project_stage_id.start_date)
    if date_stage_start_error:
      lst = [
        f'\t- {w.wp_code}: {w.name} - {w.project_stage_id.stage_code}: {w.project_stage_id.name}'
        for w in date_stage_start_error]
      raise exceptions.ValidationError(
          f"Ngày bắt đầu gói việc không được nhỏ hơn ngày bắt đầu của giai đoạn. Cặp gói việc - giai đoạn lỗi gồm:\n" + '\n'.join(
              lst))
    date_stage_end_error = self.filtered(lambda
                                             rec: not rec.parent_id and rec.date_end and rec.project_stage_id.end_date and rec.date_end > rec.project_stage_id.end_date)
    if date_stage_end_error:
      lst = [
        f'\t- {w.wp_code}: {w.name} - {w.project_stage_id.stage_code}: {w.project_stage_id.name}'
        for w in date_stage_end_error]
      raise exceptions.ValidationError(
          f"Ngày kết thúc gói việc không được lớn hơn ngày kết thúc giai đoạn. Cặp gói việc - giai đoạn lỗi gồm:\n" + '\n'.join(
              lst))
    date_lt_parent_error = self.filtered(lambda
                                             rec: rec.parent_id and rec.date_start and rec.parent_id.date_start and rec.date_start < rec.parent_id.date_start)
    if date_lt_parent_error:
      lst = [
        f'\t- {w.wp_code}: {w.name} - {w.parent_id.wp_code}: {w.parent_id.name}'
        for w in date_lt_parent_error]
      raise exceptions.ValidationError(
          f"Ngày bắt đầu gói việc con không được nhỏ hơn ngày bắt đầu gói việc cha của nó. Cặp gói việc  lỗi gồm:\n" + '\n'.join(
              lst))
    date_gt_error = self.filtered(lambda
                                      rec: rec.date_start and rec.date_end and rec.project_stage_id and not (
        rec.date_start <= rec.date_end <= rec.project_stage_id.end_date))
    if date_gt_error:
      lst = [f'\t- {w.wp_code}: {w.name}' for w in date_gt_error]
      raise exceptions.ValidationError(
          f"Ngày bắt đầu gói việc không được lớn hơn ngày kết thúc gói việc. Vị trí gói việc lỗi gồm:\n" + '\n'.join(
              lst))

  @api.model
  def _name_search(self, name, args=None, operator='ilike', limit=100,
      name_get_uid=None):
    if self._context.get('import_file') and self._context.get(
        'import_order_line') in ['wbs_version.id',
                                 'en_wbs_id.id'] and self._context.get(
        'relation_id'):
      args = args or []
      args = [('wbs_version', '=', self._context.get('relation_id'))] + args
    return super()._name_search(name, args, operator, limit, name_get_uid)


class Wbs(models.Model):
  _name = 'en.wbs'
  _description = 'WBS'
  _order = 'seq_id asc'
  _inherit = 'ngsd.approval'
  _parent_store = True

  def read(self, fields_lst, load='_classic_read'):
    # if self.env['en.wbs'].sudo().search_count([('version_type', '=', 'plan')]) > 1:
    #     for rec in self.env['en.wbs'].sudo().search([('version_type', '=', 'plan')]):
    #         if rec.resource_plan_id and rec.resource_plan_id.state != 'approved':
    #             rec.with_context(allow_active=False).write({'state': 'refused'})
    return super().read(fields_lst, load=load)

  @api.model
  def get_project_name(self):
    self = self.env['en.wbs'].browse(self._context.get('active_ids'))
    return f'Sơ đồ tổ chức dự án {self.project_id.name}'

  def to_org_chart(self):
    self = self.sudo()

    # action = self.env["ir.actions.client"]._for_xml_id('ngsd_base.action_org_chart_overview')
    # action['context'] = {'wbs_id': self.id}
    # action['name'] = f'Sơ đồ tổ chức dự án {self.project_id.name}'

    base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
    report_action = 'ngsd_base.action_org_chart_overview'
    action = self.env.ref(report_action)
    record_url = f'{base_url}/web#active_id={self.id}&action={action.id}'
    client_action = {
      'type': 'ir.actions.act_url',
      'name': f'Sơ đồ tổ chức dự án {self.project_id.name}',
      'url': record_url,
    }
    return client_action

  @api.model
  def fields_view_get(self, view_id=None, view_type='form', toolbar=False,
      submenu=False):
    res = super().fields_view_get(view_id=view_id, view_type=view_type,
                                  toolbar=toolbar, submenu=submenu)
    if view_id != self.env.ref('ngsd_base.wbs_form_create_popup').id:
      return res
    doc = etree.XML(res['arch'])
    for node in doc.xpath("//header/button"):
      node.set("context", "{'allow_active': True}")
    for node in doc.xpath("//div[@name='button_box']"):
      node.set("context", "{'allow_active': True}")
    for node in doc.xpath("//page/button"):
      node.set("context", "{'allow_active': True}")
    res['arch'] = etree.tostring(doc, encoding='unicode')
    return res

  def _get_employee_domain(self, parent_id):
    domain = []
    if not parent_id:
      domain.extend([("parent_id", "=", False)])
    else:
      domain.append(("parent_id", "=", parent_id))
    return domain

  def button_sent(self):
    self.project_stage_ids._en_constrains_en_start_date()
    self.workpackage_ids._constrains_date()
    res = super().button_sent()
    return self.open_wbs_or_not() or res

  def _get_employee_data(self, level=0, position=False):
    records = self.resource_plan_id.order_line.filtered(
        lambda x: x.job_position_id.id == position)
    record = self.env['en.job.position'].browse(position)
    a = []
    for r in records:
      if f'{r.employee_id.display_name} - {r.role_id.display_name}' not in a:
        a += [f'{r.employee_id.display_name} - {r.role_id.display_name}']
    return {
      "id": record.id,
      "name": record.name,
      "title": '<br/>'.join(a),
      "className": org_chart_classes[level],
    }

  @api.model
  def _get_children_data(self, child_ids, level):
    children = []
    # default_domain = [('id', 'in', self.resource_plan_id.mapped('order_line.job_position_id').ids)]
    default_domain = []
    for employee in child_ids:
      data = self._get_employee_data(level, employee.id)
      employee_child_ids = self.env['en.job.position'].search(
          default_domain + self._get_employee_domain(employee.id))
      if employee_child_ids:
        data.update({"children": self._get_children_data(employee_child_ids,
                                                         (level + 1) % 5)})
      children.append(data)
    return children

  @api.model
  def get_organization_data(self):
    self = self.env['en.wbs'].browse(self._context.get('active_ids'))
    # First get employee with no manager
    data = {"id": None, "name": "", "title": "", "children": []}
    if not self: return data
    # default_domain = [('id', 'in', self.resource_plan_id.mapped('order_line.job_position_id').ids)]
    default_domain = []
    domain = default_domain + self._get_employee_domain(False)
    top_employees = self.env['en.job.position'].search(domain)
    for top_employee in top_employees:
      child_data = self._get_employee_data(position=top_employee.id)
      # If any child we fetch data recursively for childs of top employee
      top_employee_child_ids = self.env['en.job.position'].search(
          default_domain + self._get_employee_domain(top_employee.id))
      if top_employee_child_ids:
        child_data.update(
            {"children": self._get_children_data(top_employee_child_ids, 1)})
      data.get("children").append(child_data)
    return data

  def action_open_new_tab(self):
    return self.open_form_or_tree_view('ngsd_base.wbs_act', False, self,
                                       {'create': 0,
                                        'default_project_id': self.id,
                                        'default_user_id': self.user_id.id})

  def button_wbs_account_report_wizard_act(self):
    record = self.env['wbs.account.report.wizard'].create(
        {'project_id': self.project_id.id, 'wbs_id': self.id})
    return record.do()

  seq_id = fields.Integer(string='💰', default=lambda self: int(
      self.env['ir.sequence'].next_by_code('seq.id')), copy=False)
  version_number = fields.Char(string='Số phiên bản', compute_sudo=True,
                               compute='_compute_version_number', store=True,
                               readonly=True, copy=False)

  @api.depends('project_id', 'project_id.en_wbs_ids', 'parent_id',
               'parent_id.child_ids', 'seq_id', 'version_type', 'state')
  def _compute_version_number(self):
    for parent in self.filtered(lambda x: x.parent_id).mapped("parent_id"):
      sequence = 1
      wbs = parent.child_ids.filtered(lambda x: x.parent_id)
      for line in sorted(wbs, key=lambda l: l.seq_id):
        line.version_number = f"{parent.technical_field_before}.{sequence}"
        sequence += 1
    for project in self.filtered(
        lambda x: not x.parent_id and x.version_type == 'plan').mapped(
        "project_id"):
      sequence = 1
      wbs = project.en_wbs_ids.filtered(
          lambda x: not x.parent_id and x.version_type == 'plan')
      for line in sorted(wbs, key=lambda l: l.seq_id):
        line.version_number = f"0.{sequence}"
        sequence += 1
    for project in self.filtered(
        lambda x: not x.parent_id and not x.version_type == 'plan').mapped(
        "project_id"):
      sequence = 1
      wbs = project.en_wbs_ids.filtered(
          lambda x: not x.parent_id and not x.version_type == 'plan')
      for line in sorted(wbs, key=lambda l: l.seq_id):
        line.version_number = f"{sequence}.0"
        sequence += 1

  parent_path = fields.Char(index=True)
  project_date_start = fields.Date(related='project_id.date_start')
  project_date = fields.Date(related='project_id.date')

  def button_version_account_report_wizard_act(self):
    return self.open_form_or_tree_view(
        'account_reports.version_account_report_wizard_act', False, False,
        {'default_current_wbs_id': self.id}, 'Chọn phiên bản so sánh', 'new')

  technical_field_27795 = fields.Boolean(string='🚑',
                                         compute='_compute_technical_field_27795')

  @api.depends('state', 'project_id')
  def _compute_technical_field_27795(self):
    for rec in self:
      technical_field_27795 = False
      if rec.state not in ['approved', 'refused'] or not rec.project_id:
        rec.technical_field_27795 = technical_field_27795
        continue
      base_line = self.env['en.wbs'].search(
          [('project_id', '=', rec.project_id.id), ('state', '=', 'approved')],
          order='id desc', limit=1)
      if rec.state == 'approved' and base_line and rec._origin.id == base_line.id:
        technical_field_27795 = True
      if rec.state == 'refused' and (
          not base_line or base_line.seq_id < rec.seq_id):
        technical_field_27795 = True
      if self.env['en.wbs'].search_count(
          [('project_id', '=', rec.project_id.id),
           ('state', '=', 'draft')]) >= 1:
        technical_field_27795 = False
      rec.technical_field_27795 = technical_field_27795

  def button_new_version_wbs(self):
    # raise UserError('Bạn không được phép tạo WBS tại thời điểm này')
    if not self.technical_field_27795:
      raise UserError('WBS này không được phép Tạo phiên bản mới')
    if not self.project_id.project_decision_ids.filtered(
        lambda d: d.state == 'approved'):
      raise UserError(
          "Dự án chưa có QĐ Thành lập dự án, vui lòng tạo quyết định trước.")
    return {
      'name': 'Xác nhận',
      'type': 'ir.actions.act_window',
      'view_mode': 'form',
      'views': [(False, 'form')],
      'res_model': 'new.version.wbs.wizard',
      'context': {
        'default_wbs_id': self.id,
      },
      'target': 'new',
    }

  def button_duplicate_wbs(self):
    if not self.technical_field_27795:
      raise UserError('WBS này không được phép Tạo phiên bản mới')
    newest_resource = self.env['en.resource.planning'].search(
        [('project_id', '=', self.project_id.id), ('state', '=', 'approved')],
        order='id desc', limit=1)
    new_wbs = self.with_context(skip_constrains_start_deadline_date=True).copy(
        {'version_type': 'plan', 'resource_plan_id': newest_resource.id,
         'active': True, 'created_by_wbs_id': self.id,
         'parent_id': self.parent_id.id or self.id})
    for stage in self.project_stage_ids:
      stage.with_context(skip_constrains_start_deadline_date=True,
                         newest_resource=newest_resource.id).copy(
          {'wbs_version': new_wbs.id, 'wbs_version_old': self.id})
    return self.open_create_wbs_popup(new_wbs)

  def button_duplicate_wbs_no_vals(self):
    if not self.technical_field_27795:
      raise UserError('WBS này không được phép Tạo phiên bản mới')
    newest_resource = self.env['en.resource.planning'].search(
        [('project_id', '=', self.project_id.id), ('state', '=', 'approved')],
        order='id desc', limit=1)
    new_wbs = self.copy(
        {'version_type': 'plan', 'resource_plan_id': newest_resource.id,
         'active': True, 'created_by_wbs_id': self.id,
         'parent_id': self.parent_id.id or self.id})
    return self.open_create_wbs_popup(new_wbs)

  def open_create_wbs_popup(self, wbs):
    return {
      'name': 'Tạo phiên bản mới',
      'type': 'ir.actions.act_window',
      'view_mode': 'form',
      'view_type': 'form',
      'views': [(self.env.ref('ngsd_base.wbs_form_create_popup').id, 'form')],
      'view_id': self.env.ref('ngsd_base.wbs_form_create_popup').id,
      'res_model': 'en.wbs',
      'res_id': wbs.id,
      'target': 'current',
      'context': {
        'create': 0,
        'active_test': False,
        'no_clean_inactive': True,
      }
    }

  def button_confirm_create_wbs(self):
    self.sudo().write({'active': True})
    return self.open_wbs_or_not()

  def open_wbs_or_not(self):
    if self._context.get('allow_active'):
      return self.open_form_or_tree_view('ngsd_base.wbs_act', False, self,
                                         {'create': 0})
    return

  created_by_wbs_id = fields.Many2one('en.wbs', readonly=1)

  def unlink(self):
    if any(
        rec.state in ['approved', 'inactive', 'refused', 'awaiting'] for rec in
        self):
      raise exceptions.UserError(
          'Không cho phép xóa WBS ở trạng thái khác Nháp')
    self.env['project.task'].search(
        [('en_task_position.wbs_version', 'in', self.ids)]).sudo().unlink()
    self.env['en.workpackage'].search(
        [('wbs_version', 'in', self.ids)]).sudo().unlink()
    self.env['en.project.stage'].search(
        [('wbs_version', 'in', self.ids)]).sudo().unlink()
    return super().unlink()

  def button_approved(self):
    self = self.sudo()
    rslt = super().button_approved()
    if rslt:
      self.write(
          {'seq_id': int(self.env['ir.sequence'].next_by_code('seq.id'))})
      self.search(
          [('project_id', '=', self.project_id.id), ('id', '!=', self.id),
           ('state', '=', 'approved')]).write({'state': 'inactive'})
      tasks = self.env['project.task'].search([('en_task_position', 'child_of',
                                                (
                                                    self.workpackage_ids | self.project_stage_ids.mapped(
                                                    'order_line')).ids)])
      for task in tasks:
        task = task.sudo()
        task.related_task_id.timesheet_ids.ot_id.write({'task_id': task.id})
        task.related_task_id.timesheet_ids.write({'task_id': task.id})
        self.env['en.overtime.plan'].sudo().search(
            [('en_work_id', '=', task.related_task_id.id)]).write(
            {'en_work_id': task.id})
        # task.send_notify('Bạn mới được giao công việc', task.en_handler, 'công việc')
    return rslt

  def _compute_sent_ok(self):
    for rec in self:
      rec.sent_ok = True

  def name_get(self):
    return [(rec.id,
             f"[{rec.version_number}] {dict(rec.fields_get(['version_type'])['version_type']['selection'])[rec.version_type] if rec.version_type else ''}")
            for rec in self]

  project_id = fields.Many2one(string='Dự án', comodel_name='project.project',
                               required=True, states=READONLY_STATES)

  def get_flow_domain(self):
    return [('model_id.model', '=', self._name), '|',
            ('project_ids', '=', False),
            ('project_ids', '=', self.project_id.id)]

  # @api.constrains('version_number', 'project_id', 'state')
  # def _constrains_en_version_number(self):
  #     if any(self.search_count([('project_id', '=', rec.project_id.id), ('version_number', '=', rec.version_number), ('state', '!=', 'refused')]) > 1 for rec in self):
  #         raise exceptions.ValidationError('Số phiên bản đã tồn tại. Không thể tạo')
  #     for rec in self:
  #         lg = self.search([('id', '!=', rec.id), ('project_id', '=', rec.project_id.id), ('state', '!=', 'refused')], limit=1, order='technical_field_before desc')
  #         lg = self.search([('id', '!=', rec.id), ('project_id', '=', rec.project_id.id), ('technical_field_before', '=', lg.technical_field_before), ('state', '!=', 'refused')], limit=1, order='technical_field_after desc')
  #         if rec.technical_field_before < lg.technical_field_before or (rec.technical_field_before == lg.technical_field_before and rec.technical_field_after <= lg.technical_field_after):
  #             raise exceptions.ValidationError(f'Không thể tạo phiên bản có số nhỏ hơn {lg.version_number}')

  parent_id = fields.Many2one(string='Thuộc về baseline', comodel_name='en.wbs',
                              compute_sudo=True, compute='_compute_parent_id',
                              store=True)

  @api.depends('version_type', 'project_id', 'state')
  def _compute_parent_id(self):
    for rec in self:
      parent_id = self.env['en.wbs']
      if rec.version_type == 'baseline': parent_id = False
      if rec.version_type == 'plan':
        parent_id = self.env['en.wbs'].search(
            [('version_type', '=', 'baseline'),
             ('project_id', '=', rec.project_id.id),
             ('state', 'in', ['approved', 'inactive']),
             ('id', '<', rec._origin.id)], limit=1,
            order='technical_field_before desc')
      rec.parent_id = parent_id

  child_ids = fields.One2many(string='Plan', comodel_name='en.wbs',
                              inverse_name='parent_id')
  technical_field_before = fields.Integer(string='🪙', compute_sudo=True,
                                          compute='_compute_technical_field_beter',
                                          store=True)
  technical_field_after = fields.Integer(string='🪙', compute_sudo=True,
                                         compute='_compute_technical_field_beter',
                                         store=True)

  @api.depends('version_number')
  def _compute_technical_field_beter(self):
    for rec in self:
      try:
        version_part = rec.version_number.split('.')
        rec.technical_field_before = int(version_part[0])
        rec.technical_field_after = int(version_part[1])
      except:
        rec.technical_field_before = 0
        rec.technical_field_after = 0

  user_id = fields.Many2one(string='Người phụ trách', comodel_name='res.users',
                            required=True,
                            states={
                              'approved': [('readonly', True)],
                              'inactive': [('readonly', True)],
                              'refused': [('readonly', True)],
                            })

  @api.onchange('project_id')
  def en_onchange_project_id(self):
    self.user_id = self.project_id.user_id

  version_type = fields.Selection(string='Loại phiên bản',
                                  selection=[('baseline', 'Baseline'),
                                             ('plan', 'Plan')], store=True,
                                  compute_sudo=True,
                                  compute='_compute_version_type')

  @api.depends('state')
  def _compute_version_type(self):
    for rec in self:
      version_type = 'plan'
      if rec.state in ['approved', 'inactive']:
        version_type = 'baseline'
      rec.version_type = version_type

  def button_draft(self):
    if not self.env.user.has_group('project.group_project_manager'):
      return
    for rec in self:
      if rec.state != 'refused': continue
      rec.write({'seq_id': int(self.env['ir.sequence'].next_by_code('seq.id')),
                 'state': 'draft'})

  state = fields.Selection(string='Trạng thái', selection=[('draft', 'Nháp'),
                                                           ('awaiting',
                                                            'Chưa duyệt'),
                                                           ('approved',
                                                            'Đã duyệt'),
                                                           ('refused',
                                                            'Bị từ chối'),
                                                           ('inactive',
                                                            'Hết hiệu lực')],
                           default='draft', required=True, readonly=True,
                           copy=False)
  resource_plan_id = fields.Many2one(string='Kế hoạch nguồn lực',
                                     domain="[('project_id', '=', project_id),('state','=','approved')]",
                                     comodel_name='en.resource.planning',
                                     required=False,
                                     compute='_compute_resource_plan')
  planned_resource = fields.Float(string='Tổng nguồn lực (MM)', default=0,
                                  compute_sudo=True,
                                  compute='_compute_planned_resource')

  @api.depends('project_id', 'project_id.en_resource_id')
  def _compute_resource_plan(self):
    for rec in self:
      rec.resource_plan_id = rec.project_id.en_resource_id if rec.project_id.en_resource_id else False

  def draft_state(self):
    return 'draft'

  def sent_state(self):
    return 'awaiting'

  def approved_state(self):
    return 'approved'

  def refused_state(self):
    return 'refused'

  workpackage_ids = fields.One2many(string='Gói công việc',
                                    comodel_name='en.workpackage',
                                    inverse_name='wbs_version',
                                    states={
                                      'refused': [('readonly', True)],
                                      'inactive': [('readonly', True)],
                                    })

  project_stage_ids = fields.One2many(string='Giai đoạn',
                                      comodel_name='en.project.stage',
                                      inverse_name='wbs_version',
                                      # states={
                                      #     'approved': [('readonly', True)],
                                      #     'refused': [('readonly', True)],
                                      #     'inactive': [('readonly', True)], # tạm thời bỏ readonly
                                      # }
                                      )
  en_wbs_task_ids = fields.One2many(string='Công việc',
                                    comodel_name='project.task',
                                    inverse_name='en_wbs_id')

  project_stage_count = fields.Integer(string='Giai đoạn', compute_sudo=True,
                                       compute='_compute_project_stage_count')

  @api.depends('project_stage_ids')
  def _compute_project_stage_count(self):
    for rec in self:
      rec.project_stage_count = len(rec.project_stage_ids)

  def to_project_stage(self):
    return self.open_form_or_tree_view('ngsd_base.project_stage_act', False,
                                       self.project_stage_ids, {
                                         'create': self.state not in READONLY_STATES.keys(),
                                         'edit': self.state not in READONLY_STATES.keys(),
                                         'delete': self.state not in READONLY_STATES.keys(),
                                         'default_project_id': self.project_id.id,
                                         'default_wbs_version': self.id,
                                         'default_date_start': self.project_date_start,
                                         'default_date_end': self.project_date})

  @api.depends('resource_plan_id', 'resource_plan_id.order_line')
  def _compute_planned_resource(self):
    for rec in self:
      planned_resource = 0
      for line in rec.resource_plan_id.order_line:
        planned_resource += line.mm * line.workload
      rec.planned_resource = planned_resource

  @api.model_create_multi
  def create(self, vals_list):
    # Handle both single record and batch creation
    if not isinstance(vals_list, list):
      vals_list = [vals_list]

    need_check_list = []
    for vals in vals_list:
      need_check_constrains_start_deadline_date = self.check_need_en_constrains_start_deadline_date(
        vals)
      need_check_list.append(need_check_constrains_start_deadline_date)

    res = super(Wbs, self.with_context(
        skip_constrains_start_deadline_date=any(need_check_list))).create(
      vals_list)

    if any(need_check_list):
      res.workpackage_ids.task_ids._en_constrains_start_deadline_date()
    return res

  def write(self, vals):
    # Xử lý tình huống xóa workpackage con của wbs
    if vals.get('workpackage_ids'):
      workpackage_ids = [item for item in vals['workpackage_ids'] if
                         not isinstance(item, list) or item[0] != 4]
      if workpackage_ids:
        vals['workpackage_ids'] = workpackage_ids
      else:
        vals.pop('workpackage_ids')
    need_check_constrains_start_deadline_date = self.check_need_en_constrains_start_deadline_date(
        vals)
    if self._context.get('allow_active'):
      vals['active'] = True
    if vals.get('active'):
      self.check_all_task_constrain()
    res = super(Wbs, self.with_context(
        skip_constrains_start_deadline_date=need_check_constrains_start_deadline_date)).write(
        vals)
    if need_check_constrains_start_deadline_date:
      self.workpackage_ids.task_ids._en_constrains_start_deadline_date()
    return res

  def check_need_en_constrains_start_deadline_date(self, vals):
    if self._context.get('skip_constrains_start_deadline_date'):
      return True
    workpackage_ids = vals.get('workpackage_ids') or []
    for w in workpackage_ids:
      if type(w) == list and w[0] in [0, 1] and 'task_ids' in w[2]:
        return True
    return False

  def check_all_task_constrain(self):
    tasks = self.en_wbs_task_ids | self.workpackage_ids.task_ids
    tasks._en_constrains_start_deadline_date()

  active = fields.Boolean(default=True)
  old_migrate = fields.Boolean(default=False, readonly=1)
  en_mm_conversion = fields.Float(related='resource_plan_id.mm_conversion',
                                  string='Tổng MM quy đổi của dự án')
  en_mh_total = fields.Float(related='resource_plan_id.hours_total',
                             string='Tổng MH của kế hoạch nguồn lực')
  en_md = fields.Float(related='resource_plan_id.en_md',
                       string='Tổng nguồn lực (MD)')
  en_wbs_mh_total = fields.Float('Tổng số giờ dự kiến',
                                 compute='_compute_wbs_mh_total')

  @api.depends('en_wbs_task_ids')
  def _compute_wbs_mh_total(self):
    for rec in self:
      hours_planned = 0
      for task in rec.en_wbs_task_ids:
        hours_planned += task.planned_hours
      rec.en_wbs_mh_total = hours_planned

  def import_workpackage_action(self):
    action = self.env['ir.actions.client']._for_xml_id(
        'ngsd_base.action_en_workpackage_line_import')
    action['params']['res_id'] = self.id
    return action

  def import_project_stage_action(self):
    action = self.env['ir.actions.client']._for_xml_id(
        'ngsd_base.action_en_project_stage_line_import')
    action['params']['res_id'] = self.id
    return action

  def import_project_task_action(self):
    action = self.env['ir.actions.client']._for_xml_id(
        'ngsd_base.action_project_task_line_import')
    action['params']['res_id'] = self.id
    return action

  def action_open_wbs_export(self):
    return {
      'type': 'ir.actions.act_window',
      'name': 'Xuất WBS',
      'res_model': 'en.wbs',
      'view_mode': 'tree,form',
      'target': 'current',
      'context': {
        'show_export_hint': True,
        'search_default_id': [self.id],
      },
    }


class RiskScope(models.Model):
  _name = 'en.risk.scope'
  _description = 'Phạm vi rủi ro'

  code = fields.Integer(string='Mã mức độ rủi ro', required=True, default=0)
  name = fields.Char(string='Tên mức độ rủi ro', required=True)

  @api.constrains('code')
  def _constrains_code(self):
    if any(self.search_count([('code', '=', rec.code)]) > 1 for rec in self):
      raise exceptions.ValidationError('Các mã không được trùng nhau!')


class IsoType(models.Model):
  _name = 'en.iso.type'
  _description = 'Loại ISO'

  code = fields.Integer(string='Mã loại ISO', required=True, default=0)
  name = fields.Char(string='Tên loại ISO', required=True)

  @api.constrains('code')
  def _constrains_code(self):
    if any(self.search_count([('code', '=', rec.code)]) > 1 for rec in self):
      raise exceptions.ValidationError('Các mã không được trùng nhau!')


class StrategyHandle(models.Model):
  _name = 'en.strategy.handle'
  _description = 'Chiến lược xử lý'

  code = fields.Char(string='Mã chiến lược xử lý', required=True, default='')
  name = fields.Char(string='Tên chiến lược xử lý', required=True)

  @api.constrains('code')
  def _constrains_code(self):
    if any(self.search_count([('code', '=', rec.code)]) > 1 for rec in self):
      raise exceptions.ValidationError('Các mã không được trùng nhau!')

  type = fields.Selection(string='Rủi Ro/Cơ Hội',
                          selection=[('rr', 'Rủi ro'), ('ch', 'Cơ hội')])


class EffectLevel(models.Model):
  _name = 'en.effect.level'
  _description = 'Mức độ ảnh hưởng'

  name = fields.Char(string='Mức độ ảnh hưởng', required=True)
  score = fields.Integer(string='Thang điểm', default=0)
  finance = fields.Text(string='Tài chính')
  prestige = fields.Text(string='Uy tín')
  activ = fields.Text(string='Hoạt động và nguồn lực')
  legal = fields.Text(string='Pháp lý')
  cost_handle = fields.Text(string='Chi phí khắc phục')


class RiskLevel(models.Model):
  _name = 'en.risk.level'
  _description = 'Mức độ rủi ro'

  name = fields.Char(string='Mức độ Rủi ro/Cơ hội', required=True)
  min = fields.Integer(string='Điểm chặn dưới', default=0)
  max = fields.Integer(string='Điểm chặn trên', default=0)

  @api.constrains('min', 'max', 'type')
  def _en_constrains_min_max(self):
    if any(rec.min > rec.max for rec in self):
      raise exceptions.ValidationError(
          'Điểm chặn dưới không thể lớn hơn điểm chặn trên!')
    for rec in self:
      if self.search_count(
          [('id', '!=', rec.id), ('max', '>=', rec.min), ('min', '<=', rec.max),
           ('type', '=', rec.type)]):
        raise UserError(
            f"Khoảng điểm bị trùng lặp với mức độ {', '.join(self.search([('id', '!=', rec.id), ('max', '>=', rec.min), ('min', '<=', rec.max), ('type', '=', rec.type)]).mapped('name'))}!")

  type = fields.Selection(string='Loại',
                          selection=[('rr', 'Rủi ro'), ('ch', 'Cơ hội')])
  definition = fields.Text(string='Định nghĩa mức độ rủi ro/ cơ hội')
  priority = fields.Selection(string='Mức độ ưu tiên',
                              selection=[('0', 'Thấp'), ('1', 'Trung bình'),
                                         ('2', 'Cao'), ('3', 'Rất cao')],
                              default='0', required=1)
  strategy_handle = fields.Char(string='Chiến lược xử lý')
  method_handle = fields.Char(string='Biện pháp xử lý')


class QaEvaluate(models.Model):
  _name = 'qa.evaluate'
  _description = 'QaEvaluate'

  project_id = fields.Many2one('project.project', 'Dự án')
  date = fields.Date('Ngày tạo',
                     default=lambda self: fields.Date.Date.Date.context_today(self),
                     required=True)
  qa_valuate = fields.Html('Mô tả', required=False)
  type = fields.Selection(string="Loại", selection=[('on_time', 'Đúng hạn'),
                                                    ('overdue', 'Trễ hạn'), ],
                          required=False)
  state = fields.Text(string="Ngày", required=False)  # xoá
  slow_progress = fields.Html(string="Tiến độ dự án")
  not_stay_on_track = fields.Html(string="Chất lượng dự án")
  non_compliance = fields.Html(string="Tuân thủ quy trình")
  acceptance_payment = fields.Html(string="Nghiệm Thu/ thanh toán")

  code_project = fields.Char(related='project_id.en_code', store=True)
  email_qa = fields.Char('Email QA', compute='_compute_email_qa', store=True)
  email_pm = fields.Char('Email PM', compute='_compute_email_pm', store=True)

  @api.depends('project_id', 'project_id.en_project_qa_id',
               'project_id.en_project_qa_id.employee_id.work_email')
  def _compute_email_qa(self):
    for rec in self:
      if rec.project_id and rec.project_id.en_project_qa_id:
        rec.email_qa = rec.project_id.en_project_qa_id.employee_id.work_email
      else:
        rec.email_qa = False

  @api.depends('project_id', 'project_id.user_id',
               'project_id.user_id.employee_id.work_email')
  def _compute_email_pm(self):
    for rec in self:
      if rec.project_id and rec.project_id.user_id:
        rec.email_pm = rec.project_id.user_id.employee_id.work_email
      else:
        rec.email_pm = False

  @api.model_create_multi
  def create(self, vals_list):
    # Handle both single record and batch creation
    if not isinstance(vals_list, list):
      vals_list = [vals_list]

    res = super().create(vals_list)
    for record, vals in zip(res, vals_list):
      if vals.get('date'):
        record.create_date = vals.get('date')
      if not record.date:
        record.date = record.create_date
    return res


class Survey(models.Model):
  _name = 'qa.survey'
  _description = "Survey"

  date = fields.Date('Ngày tạo',
                     default=lambda self: fields.Date.Date.Date.context_today(self),
                     required=True)
  project_id = fields.Many2one('project.project', 'Dự án')
  point = fields.Integer(string="Điểm")
  customer_comment = fields.Char(string="Ý kiến khách hàng")
  phase = fields.Char(string="Giai đoạn")


class RiskStage(models.Model):
  _name = 'en.risk.stage'
  _description = 'Tình trạng'

  name = fields.Char(string='Giai đoạn rủi ro')


class RiskType(models.Model):
  _name = 'en.risk.type'
  _description = 'Loại rủi ro'

  name = fields.Char(string='Loại rủi ro')
  code = fields.Integer(string='Mã loại rủi ro', default=0)

  @api.constrains('code')
  def _constrains_code(self):
    if any(self.search_count([('code', '=', rec.code)]) > 1 for rec in self):
      raise exceptions.ValidationError('Mã loại rủi ro đã bị trùng')


class Risk(models.Model):
  _name = 'en.risk'
  _description = 'Rủi ro/Cơ hội'

  type = fields.Selection(string='Phân loại',
                          selection=[('rr', 'Rủi ro'), ('ch', 'Cơ hội')],
                          required=True)
  stage_id = fields.Many2one(string='Tình trạng', comodel_name='en.risk.stage',
                             index=True,
                             default=lambda self: self.env[
                               'en.risk.stage'].search([], limit=1),
                             readonly=False, store=True,
                             copy=False, group_expand='_read_group_stage_ids')

  @api.model
  def _read_group_stage_ids(self, stages, domain, order):
    stage_ids = stages._search([], order=order, access_rights_uid=SUPERUSER_ID)
    return stages.browse(stage_ids)

  project_id = fields.Many2one(string='Dự án', comodel_name='project.project',
                               required=True, readonly=False,
                               ondelete='cascade')
  project_stage_id = fields.Many2one(string='Giai đoạn',
                                     domain="[('project_id','=',project_id)]",
                                     comodel_name='en.project.stage')
  creator_id = fields.Many2one(string='Người nhận diện',
                               comodel_name='res.users', required=True,
                               default=lambda self: self.env.user)
  en_create_date = fields.Date(string='Ngày nhận diện',
                               default=lambda self: fields.Date.today(),
                               required=True)
  name = fields.Char(string='Tên rủi ro/cơ hội', required=True)
  risk_type_id = fields.Many2one(string='Loại rủi ro/cơ hội',
                                 comodel_name='en.risk.type', required=True)
  risk_scope_id = fields.Many2one(string='Phạm vi rủi ro/cơ hội',
                                  comodel_name='en.risk.scope')
  iso_type_id = fields.Many2one(string='Loại ISO', comodel_name='en.iso.type')
  security = fields.Selection(string='Bảo mật',
                              selection=[('nb', 'Nội bộ'), ('bn', 'Bên ngoài')])
  strategy_handle_id = fields.Many2one(string='Chiến lược xử lý',
                                       comodel_name='en.strategy.handle',
                                       required=True)
  deadline = fields.Datetime(string='Hạn hoàn thành', required=True)

  @api.constrains('en_create_date', 'deadline')
  def _constrains_deadline(self):
    for rec in self:
      if not rec.en_create_date or not rec.deadline: continue
      create_date = timezone(self.env.user.tz or 'UTC').localize(
          datetime.combine(rec.en_create_date, time.min)).astimezone(
        UTC).replace(
          tzinfo=None)
      if create_date > rec.deadline: raise exceptions.ValidationError(
          'Hạn hoàn thành phải lớn hơn hoặc bằng Ngày nhận diện!')

  possible_id = fields.Many2one("en.possible.rate",
                                string='Đánh giá khả năng xảy ra',
                                required=True)
  impact = fields.Selection(string='Mức độ tác động',
                            selection=[('rc', 'Rất cao'), ('c', 'Cao'),
                                       ('tb', 'Trung bình'), ('t', 'Thấp')])
  effect_level_id = fields.Many2one(string='Đánh giá ảnh hưởng',
                                    comodel_name='en.effect.level',
                                    required=True)
  risk_level_id = fields.Many2one(string='Mức độ rủi ro/cơ hội',
                                  comodel_name='en.risk.level', tracking=True,
                                  compute='compute_to_risk_level', store=True)
  risk_level_priority = fields.Selection(related='risk_level_id.priority')
  priority = fields.Selection(string='Mức độ ưu tiên',
                              selection=[('0', 'Thấp'), ('1', 'Trung bình'),
                                         ('2', 'Cao'), ('3', 'Rất cao'), ],
                              required=True)
  priority_id = fields.Many2one('en.problem.priority', string='Mức độ ưu tiên')
  priority_new = fields.Char(string="Mức độ ưu tiên",
                             compute='compute_to_risk_level', readonly=True)
  date_end = fields.Date(string='Ngày đóng', readonly=True, copy=False)
  pic_id = fields.Many2one(string='Người chịu trách nhiệm',
                           comodel_name='res.users',
                           default=lambda self: self.env.user, required=True)
  tic_id = fields.Many2one(string='Nhóm chịu trách nhiệm',
                           comodel_name='crm.team',
                           default=lambda self: self.env.user.sale_team_id)

  descrip = fields.Text(string='Mô tả rủi ro/cơ hội', required=True)
  against = fields.Text(string='Biện pháp phòng chống')
  recover = fields.Text(string='Kế hoạch xử lý rủi ro/cơ hội', required=True)
  analyst = fields.Text(string='Nguyên nhân chi tiết', required=True)
  # leftover = fields.Text(string='Rủi ro/cơ hội còn lại', required=True)
  risk_leftover = fields.One2many('en.risk.leftover', 'risk_id',
                                  'Rủi ro/cơ hội còn lại')

  # state = fields.Selection(string='Tình trạng', selection=[('a', 'Mới'), ('b', 'Tiếp nhận'), ('c', 'Giao việc'), ('d', 'Đang xử lý'), ('e', 'Đã xử lý'), ('f', 'Hoàn thành'), ('g', 'Hủy')], default='a')

  @api.depends('possible_id', 'effect_level_id', 'type')
  def compute_to_risk_level(self):
    for rec in self:
      risk_level_id = False
      if rec.possible_id and rec.effect_level_id and rec.type:
        rate = rec.possible_id.rate * rec.effect_level_id.score
        risk_level_id = self.env['en.risk.level'].search(
            [('max', '>=', rate), ('min', '<=', rate), ('type', '=', rec.type)],
            order='max desc, min desc, id desc', limit=1)
      rec.risk_level_id = risk_level_id
      if risk_level_id and hasattr(risk_level_id, 'name'):
        rec.priority_new = risk_level_id.name
      else:
        rec.priority_new = False

  @api.model_create_multi
  def create(self, vals_list):
    for vals in vals_list:
      if vals.get('state', 'a') == 'f':
        vals['date_end'] = fields.Date.today()
      if vals.get('stage_id'):
        stage_id = self.env['en.risk.stage'].browse(vals.get('stage_id'))
        if stage_id.name == 'Hoàn thành':
          vals['date_end'] = fields.Date.today()
    return super().create(vals_list)

  def write(self, vals):
    if vals.get('state') == 'f':
      vals['date_end'] = fields.Date.today()
    if vals.get('stage_id'):
      stage_id = self.env['en.risk.stage'].browse(vals.get('stage_id'))
      if stage_id.name == 'Hoàn thành':
        vals['date_end'] = fields.Date.today()
      if stage_id.name == 'Đã đóng':
        record_leftover = self.env['en.risk.leftover'].search(
            [('risk_id', '=', self.id)],
            order='en_create_date ASC'
        )
        if record_leftover[-1].risk_level_id.name != 'Thấp':
          if vals.get('risk_leftover'):
            result = [rec for rec in vals.get('risk_leftover') if
                      rec[1] == record_leftover[-1].id]
            if isinstance(result[0][-1], dict):
              risk_level_id = self.env['en.risk.level'].browse(
                  result[0][-1].get('risk_level_id'))
              if risk_level_id.name != 'Thấp':
                raise UserError(
                    "Mức độ rủi ro/cơ hội chưa ở mức Thấp, chưa thể Đóng rủi ro này")
            else:
              raise UserError(
                  "Mức độ rủi ro/cơ hội chưa ở mức Thấp, chưa thể Đóng rủi ro này")
          else:
            raise UserError(
                "Mức độ rủi ro/cơ hội chưa ở mức Thấp, chưa thể Đóng rủi ro này")

    return super().write(vals)


class RiskLeftOver(models.Model):
  _name = "en.risk.leftover"
  _description = "Rủi ro, cơ hội còn lại"

  risk_id = fields.Many2one('en.risk', 'Rủi ro/cơ hội chính')
  en_create_date = fields.Date(string='Ngày đánh giá',
                               default=lambda self: fields.Date.today(),
                               required=True)
  risk_level_id = fields.Many2one(string='Mức độ rủi ro/cơ hội',
                                  comodel_name='en.risk.level', tracking=True,
                                  required=True)
  pic_id = fields.Many2one(string='Người chịu trách nhiệm',
                           comodel_name='res.users',
                           default=lambda self: self.env.user, required=True)
  combination = fields.Text(string='Phối hợp thực hiện', required=True)
  detailed_cause = fields.Text(string='Nguyên nhân chi tiết', required=True)
  plan = fields.Text(string='Kế hoạch xử lý', required=True)
  en_deadline_date = fields.Date(string='Hạn xử lý', required=True)


class EnPossibleRate(models.Model):
  _name = "en.possible.rate"
  _description = "Khả năng xảy ra"

  name = fields.Char('Mức độ khả năng xảy ra', required=1)
  rate = fields.Integer('Thang điểm', required=0)
  criteria = fields.Text('Các tiêu chí đánh giá', required=0)


class EnRiskSolution(models.Model):
  _name = "en.risk.solution"
  _description = "Các biện pháp xử lý"

  to_approve_date = fields.Datetime('Ngày đề xuất', readonly=1)
  user_id = fields.Many2one('res.users', string='Người đề xuất', readonly=1)
  risk_id = fields.Many2one('en.risk', string='Rủi ro/ Cơ hội', required=1,
                            ondelete='cascade', readonly=1)
  risk_level_id = fields.Many2one(related='risk_id.risk_level_id')
  name = fields.Text('Biện pháp', required=1, readonly=True,
                     states={'draft': [('readonly', False)]})
  state = fields.Selection(
      selection=[('draft', 'Mới'), ('to_approve', 'Chờ duyệt'),
                 ('approved', 'Đã duyệt'), ('refused', 'Từ chối')], required=1,
      default='draft', string='Trạng thái', readonly=1)
  note = fields.Text('Ghi chú', readonly=True,
                     states={'draft': [('readonly', False)]})


class EnResponseRate(models.Model):
  _name = "en.response.rate"
  _description = "Cam kết tỉ lệ phản hồi"

  project_id = fields.Many2one('project.project', string='Dự án', required=1,
                               ondelete='cascade')
  start_date = fields.Date('Từ ngày', required=1)
  end_date = fields.Date('Đến ngày', required=1)
  rate = fields.Float('Tỉ lệ (%)', required=1)

  @api.constrains('start_date', 'end_date', 'rate')
  def check_data(self):
    for rec in self:
      if rec.start_date > rec.end_date:
        raise UserError('Giá trị Từ ngày không được lớn hơn giá trị Đến ngày')
      if rec.rate > 1:
        raise UserError('Tỷ lệ không quá 100%')


class EnProcessingRate(models.Model):
  _name = "en.processing.rate"
  _description = "Cam kết tỉ lệ xử lý"

  project_id = fields.Many2one('project.project', string='Dự án', required=1,
                               ondelete='cascade')
  start_date = fields.Date('Từ ngày', required=1)
  end_date = fields.Date('Đến ngày', required=1)
  rate = fields.Float('Tỉ lệ (%)', required=1)

  @api.constrains('start_date', 'end_date', 'rate')
  def check_data(self):
    for rec in self:
      if rec.start_date > rec.end_date:
        raise UserError('Giá trị Từ ngày không được lớn hơn giá trị Đến ngày')
      if rec.rate > 1:
        raise UserError('Tỷ lệ không quá 100%')


class EnWorkPlans(models.Model):
  _name = 'en.work.plans'
  _description = 'Công việc hoàn thành & Kế hoạch tiếp theo'
  _rec_name = 'date_work_plan'

  date_work_plan = fields.Date('Thời gian')
  work_done = fields.Text('Công việc đã hoàn thành')
  plan_done = fields.Text('Kế hoạch 2 tuần tiếp theo')
  project_id = fields.Many2one('project.project', string="Dự án")
  total_ticket_ontime_feedback = fields.Integer('Tổng ticket đúng hạn phản hồi')
  total_ticket_due_feedback = fields.Integer('Tổng ticket đến hạn phản hồi')
  total_ticket_ontime_process = fields.Integer('Tổng ticket đúng hạn xử lý')
  total_ticket_due_process = fields.Integer('Tổng ticket đến hạn xử lý')


class ResourceProject(models.Model):
  _name = 'resource.project'
  _description = 'Danh sách nhân sự'

  type_id = fields.Many2one('en.type', 'Loại')
  employee_id = fields.Many2one(string='Nhân sự', comodel_name='hr.employee',
                                required=True,
                                context={'active_test': False}, index=True)
  email = fields.Char(string='Email', related='employee_id.work_email')
  role_id = fields.Many2one('en.role', 'Vai trò', required=False, readonly=True)
  role_ids = fields.Many2many('en.role', string='Vai trò')
  en_job_position_id = fields.Many2one('en.job.position', 'Vị trí',
                                       required=False, readonly=True)
  en_job_position_ids = fields.Many2many('en.job.position', string='Vị trí')
  date_start = fields.Date('Thời gian bắt đầu')
  date_end = fields.Date('Thời gian kết thúc')
  en_state = fields.Selection(string='Trạng thái',
                              related='employee_id.en_status')
  project_id = fields.Many2one('project.project', 'Dự án', required=True,
                               ondelete='cascade')
  department_id = fields.Many2one(related='project_id.en_department_id')
  date_leave = fields.Date('Ngày rời dự án')
  state = fields.Selection(
      selection=[('active', 'Còn hiệu lực'), ('inactive', 'Hết hiệu lực'), ],
      default='active', string='Trạng thái trong dự án')
  employee_borrow_ids = fields.Many2many('hr.employee',
                                         string='Nhân sự đang mượn',
                                         compute='_compute_employee_borrow',
                                         compute_sudo=False)
  is_borrow = fields.Boolean(compute='_compute_check_employee',
                             string='Nhân sự đi mượn', compute_sudo=True,
                             store=True)
  en_project_type_id = fields.Many2one(string='Loại dự án',
                                       comodel_name='en.project.type',
                                       related='project_id.en_project_type_id')

  @api.depends('project_id.en_department_id', 'project_id')
  def _compute_employee_borrow(self):
    self = self.sudo()
    employee_no_lender = self.env['hr.employee'].search(
        [('department_id.no_check_lender', '=', True)])
    for rec in self:
      rec.employee_borrow_ids = [(6, 0, employee_no_lender.ids)]
      for line in rec.project_id.en_department_id.employee_borrow_ids:
        rec.employee_borrow_ids = [(4, line.employee_id.id)]

  @api.depends('employee_id', 'project_id.en_department_id',
               'employee_id.department_id', 'state')
  def _compute_check_employee(self):
    for rec in self:
      if rec.state == 'inactive':
        rec.is_borrow = rec.is_borrow
        continue
      rec.is_borrow = rec.employee_id and not rec.employee_id.department_id.no_check_lender and rec.employee_id.department_id != rec.project_id.en_department_id

  @api.constrains('date_start', 'date_end', 'employee_id')
  def _constrains_employee_borrow(self):
    for rec in self:
      if not rec.is_borrow: continue
      if rec.en_project_type_id.is_presale: continue
      out_time = False
      resources = self.env['en.department.resource'].search(
          [('borrow_department_id', '=', rec.project_id.en_department_id.id),
           ('employee_id', '=', rec.employee_id.id)])
      for line in resources:
        if line.date_start <= rec.date_start <= line.date_end and line.date_start <= rec.date_end <= line.date_end and rec.is_borrow:
          out_time = True
          break
      if not out_time:
        raise ValidationError(
            f'Quãng thời gian của nhân sự {rec.employee_id.name} phải nằm trong quãng thời gian mượn của nhân sự này')

  def button_leave_project(self):
    return {
      'name': 'Xác nhận',
      'type': 'ir.actions.act_window',
      'view_mode': 'form',
      'views': [(False, 'form')],
      'res_model': 'leave.project.popup',
      'context': {
        'default_resource_project_id': self.id,
      },
      'target': 'new',
    }

  def action_leave(self, date):
    message = f'''
            Nhân sự {self.employee_id.name} rời dự án
        '''
    if date:
      resource_plan_ids = self.env['en.resource.detail'].search(
          [('order_id.project_id', '=', self.project_id.id),
           ('employee_id', '=', self.employee_id.id)])
      for resource_plan in resource_plan_ids:
        if resource_plan.date_end >= date and resource_plan.date_start < date:
          message_1 = f'''
                        Nhân sự {self.employee_id.name} Ngày kết thúc: {resource_plan.date_end.strftime('%d/%m/%Y')} → {(date - relativedelta(days=1)).strftime('%d/%m/%Y')}
                    '''
          resource_plan.sudo().write({
            'date_end': date - relativedelta(days=1)
          })
          resource_plan.order_id.sudo().message_post(body=message_1)
    self.project_id.sudo().message_post(body=message)
    self.write({
      'state': 'inactive',
      'date_leave': date
    })

  def action_inactive(self, date):
    message = f'''
            Nhân sự {self.employee_id.name} rời dự án
        '''
    self.project_id.message_post(body=message)
    self.write({
      'state': 'inactive',
      'date_leave': date
    })

  @api.constrains('date_start', 'date_end')
  def _check_date_record_employee(self):
    for rec in self:
      resource_project = self.search([('project_id', '=', rec.project_id.id),
                                      ('employee_id', '=', rec.employee_id.id),
                                      ('state', '=', 'inactive'),
                                      ('date_start', '<=', rec.date_end),
                                      ('date_leave', '>', rec.date_start)])
      if resource_project:
        raise UserError(
            f'Thời gian nhân sự {rec.employee_id.name} tham gia dự án phải nằm ngoài khoảng thời gian tham gia dự án trước đó.')

  @api.constrains('employee_id')
  def _check_employee_id(self):
    for rec in self:
      resource_project = self.search_count(
          [('project_id', '=', rec.project_id.id),
           ('employee_id', '=', rec.employee_id.id), ('state', '=', 'active')])
      if resource_project > 1:
        raise UserError('Nhân sự đang còn hiệu lực trong danh sách nhân sự')

  @api.constrains('date_start', 'date_end', 'employee_id')
  def _constrains_date_start(self):
    for rec in self:
      if rec.employee_id.en_day_layoff_from and rec.employee_id.en_day_layoff_to:
        if rec.date_start and rec.employee_id.en_day_layoff_from >= rec.date_start and rec.employee_id.en_day_layoff_from <= rec.date_end:
          raise exceptions.UserError(
              f'Nhân sự {rec.employee_id.name} đang tạm dừng trong khoảng thời gian {rec.employee_id.en_day_layoff_from.strftime("%d/%m/%Y")} - {rec.employee_id.en_day_layoff_to.strftime("%d/%m/%Y")}')
        if rec.date_start and rec.date_start >= rec.employee_id.en_day_layoff_from and rec.date_start <= rec.employee_id.en_day_layoff_to:
          raise exceptions.UserError(
              f'Nhân sự {rec.employee_id.name} đang tạm dừng trong khoảng thời gian {rec.employee_id.en_day_layoff_from.strftime("%d/%m/%Y")} - {rec.employee_id.en_day_layoff_to.strftime("%d/%m/%Y")}')
        if rec.date_end and rec.employee_id.en_day_layoff_from >= rec.date_end and rec.employee_id.en_day_layoff_to <= rec.date_end:
          raise exceptions.UserError(
              f'Nhân sự {rec.employee_id.name} đang tạm dừng trong khoảng thời gian {rec.employee_id.en_day_layoff_from.strftime("%d/%m/%Y")} - {rec.employee_id.en_day_layoff_to.strftime("%d/%m/%Y")}')
        if rec.date_end and rec.date_end >= rec.employee_id.en_day_layoff_from and rec.date_end <= rec.employee_id.en_day_layoff_to:
          raise exceptions.UserError(
              f'Nhân sự {rec.employee_id.name} đang tạm dừng trong khoảng thời gian {rec.employee_id.en_day_layoff_from.strftime("%d/%m/%Y")} - {rec.employee_id.en_day_layoff_to.strftime("%d/%m/%Y")}')
      elif rec.employee_id.en_day_layoff_from and not rec.employee_id.en_day_layoff_to:
        if rec.date_start and rec.date_start >= rec.employee_id.en_day_layoff_from:
          raise exceptions.UserError(
              f'Nhân sự {rec.employee_id.name} có ngày bắt đầu tạm dừng {rec.employee_id.en_day_layoff_from.strftime("%d/%m/%Y")}')
        if rec.date_end and rec.date_end >= rec.employee_id.en_day_layoff_from:
          raise exceptions.UserError(
              f'Nhân sự {rec.employee_id.name} có ngày bắt đầu tạm dừng {rec.employee_id.en_day_layoff_from.strftime("%d/%m/%Y")}')
      elif not rec.employee_id.en_day_layoff_from and rec.employee_id.en_day_layoff_to:
        if rec.date_start and rec.date_start <= rec.employee_id.en_day_layoff_to:
          raise exceptions.UserError(
              f'Nhân sự {rec.employee_id.name} có ngày kết thúc tạm dừng {rec.employee_id.en_day_layoff_to.strftime("%d/%m/%Y")}')
        if rec.date_end and rec.date_end <= rec.employee_id.en_day_layoff_to:
          raise exceptions.UserError(
              f'Nhân sự {rec.employee_id.name} có ngày kết thúc tạm dừng {rec.employee_id.en_day_layoff_to.strftime("%d/%m/%Y")}')
      elif rec.employee_id.departure_date and rec.date_start and rec.employee_id.departure_date <= rec.date_start:
        raise exceptions.UserError(
            f'Nhân sự {rec.employee_id.name} có ngày dừng {rec.employee_id.departure_date.strftime("%d/%m/%Y")}')
      if (
          rec.date_start and rec.project_id.date_start and rec.date_start < rec.project_id.date_start) or (
          rec.date_end and rec.project_id.date and rec.date_end > rec.project_id.date):
        raise exceptions.UserError(
            f'Thời gian sử dụng nguồn lực {rec.employee_id.display_name} phải nằm trong khoảng thời gian của dự án!')
      # if rec.date_end and rec.order_id.project_id.date and rec.date_end > rec.order_id.project_id.date:
      #     raise exceptions.UserError('KHNL phải nằm trong thời gian bắt đầu và kết thúc dự án')
      if rec.date_start and rec.date_end and rec.date_start > rec.date_end:
        raise exceptions.UserError(
            f'Thời gian kết thúc sử dụng nguồn lực {rec.employee_id.display_name} ở {rec.en_job_position_id.display_name} không thể nhỏ hơn thời gian bắt đầu là {rec.date_start.strftime("%d/%m/%Y")}.')

  @api.onchange('date_start')
  def _onchange_date_start(self):
    if self.date_start and self.date_end and self.date_start > self.date_end:
      return {'warning': {
        'title': 'Cảnh báo',
        'message': f'Thời gian kết thúc sử dụng nguồn lực {self.employee_id.display_name} ở {self.en_job_position_id.display_name} không thể nhỏ hơn thời gian bắt đầu là {self.date_start.strftime("%d/%m/%Y")}.'
      }}

  @api.onchange('type_id')
  def onchange_type_id(self):
    if self.employee_id and self.employee_id.en_type_id != self.type_id:
      self.employee_id = False

  def unlink(self):
    for rec in self:
      resource_plan = self.env['en.resource.detail'].search_count(
          [('employee_id', '=', rec.employee_id.id),
           ('order_id.project_id', '=', rec.project_id.id), '|', '&',
           ('date_start', '>=', rec.date_start),
           ('date_start', '<=', rec.date_end), '&',
           ('date_end', '>=', rec.date_start),
           ('date_end', '<=', rec.date_end)])
      if resource_plan >= 1 or rec.state == 'inactive':
        raise ValidationError('Không thể xóa Nhân sự đang có KHNL')
    return super(ResourceProject, self).unlink()

  @api.model
  def fields_get(self, allfields=None, attributes=None):
    hide = ['role_id', 'en_job_position_id']
    res = super(ResourceProject, self).fields_get()
    for field in hide:
      res[field]['searchable'] = False
      res[field]['sortable'] = False
      res[field]['exportable'] = False
    return res

  domain_resource_project = fields.Char(string="Bộ lọc nguồn lực",
                                        compute="_compute_domain_resource_project")

  @api.depends('en_project_type_id', 'type_id', 'department_id',
               'employee_borrow_ids')
  def _compute_domain_resource_project(self):
    for rec in self:
      if rec.en_project_type_id.is_presale:
        domain = [('en_status', 'not in', ['inactive'])]
      else:
        domain = [
          '&',
          ('en_type_id', '=', rec.type_id.id),
          ('en_status', 'not in', ['inactive']),
          '|',
          ('department_id', '=', rec.department_id.id),
          ('id', 'in', rec.sudo().employee_borrow_ids.ids)
        ]
      rec.domain_resource_project = str(domain)


class HistoryResource(models.Model):
  _name = 'history.resource'
  _description = 'Lịch sử nguồn lực cũ'

  month = fields.Selection([
    ('1', '1'),
    ('2', '2'),
    ('3', '3'),
    ('4', '4'),
    ('5', '5'),
    ('6', '6'),
    ('7', '7'),
    ('8', '8'),
    ('9', '9'),
    ('10', '10'),
    ('11', '11'),
    ('12', '12')], string="Tháng", default=False, required=True)
  year = fields.Selection(string="Năm", selection=lambda
      self: self._calculator_year_selection(), required=True,
                          default=False)
  plan = fields.Float('Plan')
  actual = fields.Float('Actual')
  project_id = fields.Many2one('project.project', 'Dự án')

  @api.constrains('month', 'year')
  def _onchange_time_project(self):
    for rec in self:
      if rec.project_id.date_start and rec.project_id.date and rec.year and rec.month:
        month_start = rec.project_id.date_start.month
        year_start = rec.project_id.date_start.year
        month_end = rec.project_id.date.month
        year_end = rec.project_id.date.year
        if (int(rec.month) < month_start and int(rec.year) <= year_start) or (
            int(rec.month) > month_end and int(rec.year) >= year_end):
          raise ValidationError(
              'Tháng năm của Lịch sử nguồn lực phải nằm trong khoảng thời gian của dự án')

  def _calculator_year_selection(self):
    year = 2015
    list_selection = [(str(year), str(year))]
    for i in range(0, 15):
      year += 1
      list_selection.append((str(year), str(year)))

    return list_selection


class HrEmployee(models.Model):
  _inherit = 'hr.employee'

  def _name_search(self, name='', args=None, operator='ilike', limit=100,
      name_get_uid=None):
    args = args or []
    if 'ctx_domain_resource_project' in self.env.context:
      _domain = self.env.context.get('ctx_domain_resource_project')
      args.extend(eval(_domain))
    return super()._name_search(name, args, operator, limit, name_get_uid)

  def _search(self, args, offset=0, limit=None, order=None, count=False):
    args = args or []
    if 'ctx_domain_resource_project' in self.env.context:
      _domain = self.env.context.get('ctx_domain_resource_project')
      args.extend(eval(_domain))

    # In Odoo 18, handle count parameter properly
    if count:
      # For count queries, call the parent method differently
      return self.search_count(args)
    else:
      return super()._search(args, offset=offset, limit=limit, order=order)
