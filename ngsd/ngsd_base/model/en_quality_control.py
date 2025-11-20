from odoo import api, fields, models
from datetime import timedelta, datetime, time, date
from odoo.tools import config, date_utils, get_lang, html2plaintext
from dateutil.relativedelta import relativedelta
from pytz import timezone
from odoo.exceptions import UserError, ValidationError
import logging
from odoo.models import NewId

log = logging.getLogger(__name__)

READONLY_STATES = {
  'to_approve': [('readonly', True)],
  'approved': [('readonly', True)],
  'refused': [('readonly', True)],
}
EDIT_DRAFT_STATES = {
  'to_approve': [('readonly', True)],
  'approved': [('readonly', True)],
  'refused': [('readonly', True)],
  'expire': [('readonly', True)],
}

org_chart_classes = {
  0: "level-0",
  1: "level-1",
  2: "level-2",
  3: "level-3",
  4: "level-4",
}


def daterange(start_date, end_date):
  for n in range(int(((end_date + timedelta(days=1)) - start_date).days)):
    yield start_date + timedelta(n)


class QualityControl(models.Model):
  _name = 'en.quality.control'
  _description = 'Kiểm soát chất lượng'
  _order = 'seq_id asc'
  _inherit = 'ngsd.approval'
  _parent_store = True

  def name_get(self):
    names = []
    for record in self:
      name = record.name
      if record.version_number:
        name += f' ({record.version_number})'
      names.append((record.id, name))
    return names

  active = fields.Boolean(default=True)
  parent_path = fields.Char(index=True)
  seq_id = fields.Integer(string='💰', default=lambda self: int(
    self.env['ir.sequence'].next_by_code('quality.seq.id')), copy=False)
  version_number = fields.Char(string='Số phiên bản', compute_sudo=True,
                               compute='_compute_version_number', store=True,
                               readonly=True, copy=False)

  @api.depends('project_id', 'project_id.en_quality_control_ids', 'parent_id',
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
      wbs = project.en_quality_control_ids.filtered(
        lambda x: not x.parent_id and x.version_type == 'plan')
      for line in sorted(wbs, key=lambda l: l.seq_id):
        line.version_number = f"0.{sequence}"
        sequence += 1
    for project in self.filtered(
        lambda x: not x.parent_id and not x.version_type == 'plan').mapped(
        "project_id"):
      sequence = 1
      wbs = project.en_quality_control_ids.filtered(
        lambda x: not x.parent_id and not x.version_type == 'plan')
      for line in sorted(wbs, key=lambda l: l.seq_id):
        line.version_number = f"{sequence}.0"
        sequence += 1

  parent_id = fields.Many2one(string='Thuộc về baseline',
                              comodel_name='en.quality.control',
                              compute_sudo=True, compute='_compute_parent_id',
                              store=True)

  @api.depends('version_type', 'project_id', 'state')
  def _compute_parent_id(self):
    for rec in self:
      parent_id = self.env['en.quality.control']
      if rec.version_type == 'baseline': parent_id = False
      if rec.version_type == 'plan':
        parent_id = self.env['en.quality.control'].search(
            [('version_type', '=', 'baseline'),
             ('project_id', '=', rec.project_id.id),
             ('state', 'in', ['approved', 'expire']),
             ('id', '<', rec._origin.id)], limit=1,
            order='technical_field_before desc')
      rec.parent_id = parent_id

  child_ids = fields.One2many(string='Plan', comodel_name='en.quality.control',
                              inverse_name='parent_id')
  technical_field_before = fields.Integer(string='🪙', compute_sudo=True,
                                          compute='_compute_technical_field_beter',
                                          store=True)
  technical_field_after = fields.Integer(string='🪙', compute_sudo=True,
                                         compute='_compute_technical_field_beter',
                                         store=True)
  mm_rate = fields.Float(string='Đơn vị quy đổi MM',
                         states={'to_approve': [('readonly', True)],
                                 'approved': [('readonly', True)],
                                 'refused': [('readonly', True)],
                                 'expire': [('readonly', True)]},
                         required=False, related='project_id.mm_rate')

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

  version_type = fields.Selection(string='Loại phiên bản',
                                  selection=[('baseline', 'Baseline'),
                                             ('plan', 'Plan')], store=True,
                                  compute_sudo=True,
                                  compute='_compute_version_type')

  @api.depends('state')
  def _compute_version_type(self):
    for rec in self:
      version_type = 'plan'
      if rec.state in ['approved', 'expire']:
        version_type = 'baseline'
      rec.version_type = version_type

  @api.constrains('project_id', 'state')
  def _constrains_no_more_than_one(self):
    if self._context.get('import_file') and any(rec.sudo().search_count(
        [('project_id', '=', rec.project_id.id),
         ('state', 'in', ['draft', 'to_approve'])]) > 1 for rec in self):
      raise ValidationError(
        'Hiện tại đang có bản ghi KHNL chưa được duyệt, vui lòng duyệt để tạo bản ghi KHNL mới')

  @api.constrains('order_line')
  def _constrains_workload_gather_0(self):
    for line in self.order_line:
      if not line.workload > 0:
        raise ValidationError('Bạn chưa điền giá trị workload')

  def _get_employee_domain(self, parent_id):
    domain = []
    if not parent_id:
      domain.extend([("parent_id", "=", False)])
    else:
      domain.append(("parent_id", "=", parent_id))
    return domain

  @api.constrains('project_id', 'state')
  def _constrains_project_id_state(self):
    if self._context.get('import_file') and any(
        self.env['en.quality.control'].search_count(
            [('project_id', '=', rec.project_id.id),
             ('state', '=', 'draft')]) > 1 for rec in self):
      raise ValidationError(f'Bạn không thể tạo hai KHNL ở trạng thái dự kiến ')

  def action_open_new_tab(self):
    return self.open_form_or_tree_view('ngsd_base.quality_control_act', False,
                                       self, {'default_project_id': self.id})

  en_state = fields.Selection(string='Trạng thái',
                              related='project_id.en_state')

  def write(self, vals):
    before_state = {rec: rec.state for rec in self}
    res = super().write(vals)
    return res

  technical_field_27766 = fields.Boolean(string='🚑',
                                         compute='_compute_technical_field_27766')

  @api.depends('state', 'project_id')
  def _compute_technical_field_27766(self):
    for rec in self:
      technical_field_27766 = False
      if rec.state not in ['approved', 'refused'] or not rec.project_id:
        rec.technical_field_27766 = technical_field_27766
        continue
      if rec._origin.id == self.env['en.quality.control'].search(
          [('project_id', '=', rec.project_id.id), ('state', '=', 'approved')],
          order='id desc', limit=1).id:
        technical_field_27766 = True
      rec.technical_field_27766 = technical_field_27766

  def new_resource(self):
    if not self.technical_field_27766: return
    order_line = []
    for line in self.order_line:
      if (line.employee_id.en_day_layoff_from
          and line.employee_id.en_day_layoff_to and line.employee_id.en_day_layoff_from <= line.date_start
          and line.employee_id.en_day_layoff_to >= line.date_end) or (
          line.employee_id.departure_date and line.employee_id.departure_date <= line.date_start) or \
          (
              line.employee_id.en_day_layoff_from and line.employee_id.en_day_layoff_to and line.employee_id.departure_date
              and line.employee_id.en_day_layoff_from <= line.date_start and (
                  line.employee_id.en_day_layoff_to == line.employee_id.departure_date or line.employee_id.en_day_layoff_to + relativedelta(
                  days=1) == line.employee_id.departure_date)
              and line.date_end >= line.employee_id.departure_date):
        continue
      value = {
        'employee_id': line.employee_id.id,
        'workload': line.workload,
        'old_line_id': line.id,
        'task_control': line.task_control
      }
      if line.employee_id.en_day_layoff_from \
          and line.employee_id.en_day_layoff_to and line.employee_id.en_day_layoff_from <= line.date_start \
          and line.employee_id.en_day_layoff_to < line.date_end and line.employee_id.en_day_layoff_to >= line.date_start and not line.employee_id.departure_date:
        value.update({
          'date_start': line.employee_id.en_day_layoff_to + relativedelta(
            days=1),
          'date_end': line.date_end,
        })
      elif line.employee_id.en_day_layoff_from and line.employee_id.en_day_layoff_from == line.date_start and line.employee_id.departure_date \
          and line.employee_id.departure_date > line.employee_id.en_day_layoff_to and line.employee_id.departure_date <= line.date_end:
        value.update({
          'date_start': line.employee_id.en_day_layoff_to + relativedelta(
            days=1),
          'date_end': line.employee_id.departure_date - relativedelta(days=1),
        })
      elif line.employee_id.en_day_layoff_from and line.employee_id.en_day_layoff_from >= line.date_start and (
          (line.employee_id.en_day_layoff_to \
           and line.employee_id.en_day_layoff_to <= line.date_end and not line.employee_id.departure_date) or (
              line.employee_id.departure_date \
              and line.employee_id.departure_date > line.employee_id.en_day_layoff_from)):
        value.update({
          'date_start': line.date_start,
          'date_end': line.employee_id.en_day_layoff_from - relativedelta(
            days=1),
        })
      elif line.date_end and line.date_start and line.employee_id.departure_date and line.employee_id.departure_date > line.date_start and line.employee_id.departure_date <= line.date_end:
        value.update({
          'date_start': line.date_start,
          'date_end': line.employee_id.departure_date - relativedelta(days=1)
        })
      else:
        value.update({
          'date_start': line.date_start,
          'date_end': line.date_end
        })
      order_line += [(0, 0, value)]
    values = {'order_line': order_line}
    f_lst = self.fields_get()
    for f in f_lst:
      if f_lst.get(f).get('type') == 'one2many': continue
      if not f_lst.get(f).get('store'): continue
      if f_lst.get(f).get('readonly'): continue
      if f_lst.get(f).get('type') == 'many2one':
        values[f'{f}'] = self[f].id
        continue
      if f_lst.get(f).get('type') == 'many2many':
        values[f'{f}'] = [(6, 0, self[f].ids)]
        continue
      values[f'{f}'] = self[f]
    quality_control_new = self.create(values)
    view = self.env.ref('ngsd_base.quality_control_form')
    return {
      'type': 'ir.actions.act_window',
      'view_type': 'form',
      'view_mode': 'form',
      'res_model': 'en.quality.control',
      'views': [(view.id, 'form')],
      'view_id': view.id,
      'res_id': quality_control_new.id,
      'target': 'current',
    }

  @api.returns('self', lambda value: value.id)
  def copy(self, default=None):
    # raise UserError('Bạn không được phép tạo KHNL tại thời điểm này')
    default = dict(default or {})
    order_line = []
    for line in self.order_line:
      # if line.date_end < fields.Date.today(): continue
      order_line += [(0, 0, {
        'employee_id': line.employee_id.id,
        'date_start': line.date_start,
        'date_end': line.date_end,
        'workload': line.workload,
        'old_line_id': line.id,
      })]
    default['order_line'] = order_line
    return super().copy(default)

  def button_resource_account_report_wizard_act(self):
    return self.open_form_or_tree_view(
      'account_reports.resource_account_report_wizard_act', False, False,
      {'default_resource_planing_id': self.id}, 'Thông tin nguồn lực', 'new')

  def unlink(self):
    for rec in self:
      if rec.state in READONLY_STATES.keys():
        raise UserError(
          f"Bản ghi đang ở trạng thái {dict(rec.fields_get(['state'])['state']['selection'])[rec.state]} . Không thể xóa bản ghi này !")
    return super().unlink()

  # @api.constrains('order_line', 'project_id')
  def _constrains_overload(self):
    lg = self.env['res.lang']._lang_get(self.env.user.lang) or get_lang(
      self.env)

    for rec in self:
      if rec.project_id.igone_overload:
        continue
      groupby_overwork = {}
      for employee in set(rec.mapped('order_line.employee_id')):
        if not employee.en_internal_ok: continue
        for line in rec.order_line.filtered(
            lambda x: x.employee_id == employee):
          employee_txt = f'Nhân viên {employee.display_name} đã bị quá workload vào ngày'
          if employee_txt not in groupby_overwork:
            groupby_overwork.setdefault(employee_txt, [])
          datetime_start = datetime.combine(line.date_start, time.min)
          datetime_end = datetime.combine(line.date_end, time.max)
          if datetime_start > datetime_end: continue
          for date_step in date_utils.date_range(datetime_start, datetime_end,
                                                 relativedelta(days=1)):
            if round(sum(self.env['en.quality.detail'].search(
                [('order_id', '=', rec.id), ('employee_id', '=', employee.id),
                 '&', ('date_start', '<=', date_step.date()),
                 ('date_end', '>=', date_step.date())]).mapped(
                'workload')) + sum(self.env['en.quality.detail'].search(
                [('order_id.state', '=', 'approved'),
                 ('order_id.project_id', '!=', rec.project_id.id),
                 ('employee_id', '=', employee.id), '&',
                 ('date_start', '<=', date_step.date()),
                 ('date_end', '>=', date_step.date())]).mapped('workload')),
                     10) <= 1.2: continue
            if date_step.date() in groupby_overwork[employee_txt]: continue
            groupby_overwork[employee_txt] += [date_step.date()]
      expt_txt = []
      for employee in groupby_overwork:
        if not groupby_overwork.get(employee, []): continue
        dated = sorted(groupby_overwork[employee])
        dated_txt = []
        min_dated = dated[0]
        max_dated = dated[0]
        for d in dated:
          if max_dated == d or max_dated + relativedelta(days=1) == d:
            max_dated = d
            continue
          if min_dated == max_dated:
            dated_txt += [f'{max_dated.strftime(lg.date_format)}']
          else:
            dated_txt += [
              f'{min_dated.strftime(lg.date_format)} → {max_dated.strftime(lg.date_format)}']
          min_dated = d
          max_dated = d
        else:
          if min_dated == max_dated:
            dated_txt += [f'{max_dated.strftime(lg.date_format)}']
          else:
            dated_txt += [
              f'{min_dated.strftime(lg.date_format)} → {max_dated.strftime(lg.date_format)}']
        expt_txt += [f'{employee} {" và ".join(dated_txt)}']
      # expt = [f'{employee} {", ".join([d.strftime(lg.date_format) for d in sorted(groupby_overwork[employee])])}' for employee in groupby_overwork if groupby_overwork.get(employee, [])]
      if expt_txt: raise ValidationError('\n'.join(expt_txt))

  def button_to_approve(self):
    rslt = self.button_sent()
    if not rslt: return
    self._constrains_overload()
    if self.approver_id: self.send_notify(
      f'Bạn có kế hoạch {self.display_name} cần được duyệt', self.approver_id)
    self.write({'state': 'to_approve'})

  def button_approved(self):
    self = self.sudo()

    lg = self.env['res.lang']._lang_get(self.env.user.lang) or get_lang(
      self.env)
    for rec in self:
      try:
        rec._constrains_overload()
      except Exception as e:
        self.env['en.refuse.reason.wizard'].with_context(active_model=rec._name,
                                                         active_ids=rec.ids).create(
            {'name': str(e)}).do()
        view = self.env.ref('ngsd_base.message_wizard')
        context = dict(self._context or {})
        context['message'] = str(e)
        return {
          'name': 'Lỗi xác nhận',
          'type': 'ir.actions.act_window',
          'view_type': 'form',
          'view_mode': 'form',
          'res_model': 'message.wizard',
          'views': [(view.id, 'form')],
          'view_id': view.id,
          'target': 'new',
          'context': context,
        }
    rslt = super(QualityControl, self).button_approved()
    if rslt:
      self.write({'seq_id': int(
        self.env['ir.sequence'].next_by_code('quality.seq.id'))})
      self.sudo().search(
          [('project_id', '=', self.project_id.id), ('id', '<', self.id),
           ('state', '=', 'approved')]).sudo().write({'state': 'expire'})
    return rslt

  approver_id = fields.Many2one(string='Người phê duyệt',
                                states=READONLY_STATES,
                                comodel_name='res.users')
  reason = fields.Char(string='Lý do từ chối', states=READONLY_STATES,
                       copy=False, readonly=True)
  state = fields.Selection(string='Trạng thái', selection=[('draft', 'Dự kiến'),
                                                           ('to_approve',
                                                            'Chờ duyệt'),
                                                           ('approved',
                                                            'Đã duyệt'),
                                                           ('refused',
                                                            'Từ chối'),
                                                           ('expire',
                                                            'Hết hiệu lực')],
                           default='draft', readonly=True, required=True,
                           copy=False, index=True)

  def draft_state(self):
    return 'draft'

  def sent_state(self):
    return 'to_approve'

  def approved_state(self):
    return 'approved'

  def refused_state(self):
    return 'refused'

  name = fields.Char(string='Tên', default=lambda
      self: f"[{self.version_number}] {dict(self.fields_get(['version_type'])['version_type']['selection'])[self.version_type] if self.version_type else ''}",
                     states=EDIT_DRAFT_STATES, required=True)
  project_id = fields.Many2one(string='Dự án', states=READONLY_STATES,
                               comodel_name='project.project', required=True)

  def get_flow_domain(self):
    return [('model_id.model', '=', self._name), '|',
            ('project_ids', '=', self.project_id.id),
            ('project_ids', '=', False)]

  project_code = fields.Char(related='project_id.en_code', string='Mã dự án')
  user_id = fields.Many2one(string='Người tạo', states=EDIT_DRAFT_STATES,
                            comodel_name='res.users',
                            default=lambda self: self.env.user, required=True)
  order_line = fields.One2many(string='Chi tiết kiểm soát chất lượng',
                               states=EDIT_DRAFT_STATES,
                               comodel_name='en.quality.detail',
                               inverse_name='order_id', copy=False)

  mm_qa_project = fields.Float('MM dự án phân bổ cho QA',
                               compute='_compute_mm_qa_project', store=True,
                               compute_sudo=True)
  total_md = fields.Float('Tổng MD', compute='_compute_total_md', store=True,
                          compute_sudo=True)
  total_mm = fields.Float('Tổng MM', compute='_compute_total_md', store=True,
                          compute_sudo=True)

  edit_order_line = fields.Boolean(compute='_compute_edit_order_line')

  is_pm_project = fields.Boolean('PM Dự án', compute='_compute_pm_project')

  def _compute_pm_project(self):
    for rec in self:
      rec.is_pm_project = False
      if rec.project_id.en_project_qa_id.id == self.env.uid and rec.project_id.en_resource_id and rec.project_id.en_resource_id.order_line.filtered(
          lambda x: x.employee_id.user_id.id == self.env.uid):
        rec.is_pm_project = True

  @api.depends('project_id.en_resource_id')
  def _compute_edit_order_line(self):
    for rec in self:
      if rec.project_id.en_project_qa_id == self.env.user:
        rec.edit_order_line = True
      else:
        rec.edit_order_line = False

  @api.depends('order_line', 'project_id.mm_rate')
  def _compute_total_md(self):
    for rec in self:
      total_md = 0
      for line in rec.order_line:
        total_md += line.en_md
      rec.total_md = round(total_md, 2)
      rec.total_mm = round(total_md / rec.mm_rate, 2) if rec.mm_rate else 0

  @api.depends('project_id.en_resource_id', 'project_id.mm_rate')
  def _compute_mm_qa_project(self):
    for rec in self:
      total_md = 0
      if rec.project_id.en_resource_id:
        for line in rec.project_id.en_resource_id.order_line.filtered(
            lambda x: x.employee_id.user_id == rec.project_id.en_project_qa_id):
          total_md += line.en_md
      rec.mm_qa_project = round(total_md / rec.mm_rate, 2) if rec.mm_rate else 0

  def _compute_sent_ok(self):
    for rec in self:
      rec.sent_ok = True

  def read(self, fields=None, load='_classic_read'):
    if not fields or 'order_line' in fields:
      self.filtered(lambda d: d.state not in ['approved',
                                              'expire']).order_line._compute_hours_indate()
    return super().read(fields, load)


class QualityDetail(models.Model):
  _name = 'en.quality.detail'
  _description = 'Chi tiết kiểm soát chất lượng'

  old_line_id = fields.Many2one('en.quality.detail', string='Line cũ',
                                readonly=True, copy=False)

  en_user_id = fields.Many2one('res.users', string='User của nhân viên',
                               default=lambda self: self.env.user)
  order_id = fields.Many2one(string='Kiểm soát chất lượng',
                             comodel_name='en.quality.control', required=True,
                             ondelete='cascade', index=True, auto_join=True)
  employee_id = fields.Many2one(string='Tên nhân sự',
                                comodel_name='hr.employee', default=lambda
        self: self.env.user.employee_id.id, index=True)

  email = fields.Char(string='Email', related='employee_id.work_email')
  date_start = fields.Date(string='Thời gian bắt đầu', required=True,
                           index=True)
  edit_date_start = fields.Boolean(compute='_get_readonly_date')
  edit_date_end = fields.Boolean(compute='_get_readonly_date')
  project_stage_id = fields.Many2one('en.project.stage', 'Giai đoạn',
                                     domain="[('id', 'in', project_stage_ids)]")
  project_stage_ids = fields.Many2many('en.project.stage', 'Giai đoạn',
                                       compute='_compute_project_stage')
  task_control = fields.Text('Công việc kiểm soát', required=True)

  @api.depends('order_id.project_id', 'order_id.project_id.en_current_version')
  def _compute_project_stage(self):
    for rec in self:
      rec.project_stage_ids = rec.order_id.project_id.en_current_version.project_stage_ids if rec.order_id.project_id.en_current_version else False

  @api.depends('date_start', 'date_end')
  def _get_readonly_date(self):
    for rec in self:
      today_month = fields.Date.Date.Date.context_today(rec)
      date_today = today_month.day
      month_pre = (today_month - relativedelta(months=1)).replace(day=1)
      month_current = today_month.replace(day=1)
      rec.edit_date_start = False
      rec.edit_date_end = False
      if not rec.old_line_id:
        rec.edit_date_start = True
        rec.edit_date_end = True
      else:
        if date_today <= 5:
          if rec.date_start >= month_pre:
            rec.edit_date_start = True
          if rec.date_end >= month_pre:
            rec.edit_date_end = True
        else:
          if rec.date_start >= month_current:
            rec.edit_date_start = True
          if rec.date_end >= month_current:
            rec.edit_date_end = True

  @api.onchange('date_start')
  def _onchange_check_date_start(self):
    for rec in self:
      today_month = fields.Date.Date.Date.context_today(rec)
      date_today = today_month.day
      month_pre = (today_month - relativedelta(months=1)).replace(day=1)
      month_current = today_month.replace(day=1)
      if rec.old_line_id or rec.order_id.parent_id:
        if date_today <= 5:
          if rec.date_start and rec.date_start < month_pre:
            raise ValidationError(
              f'Giá trị ngày bắt đầu phải lớn hơn {month_pre.strftime("%d/%m/%Y")}')
        else:
          if rec.date_start and rec.date_start < month_current:
            raise ValidationError(
              f'Giá trị ngày bắt đầu phải lớn hơn {month_current.strftime("%d/%m/%Y")}')

  @api.onchange('date_end')
  def _onchange_check_date_end(self):
    for rec in self:
      today_month = fields.Date.Date.Date.context_today(rec)
      date_today = today_month.day
      month_pre = (today_month - relativedelta(months=1)).replace(day=1)
      month_current = today_month.replace(day=1)
      if rec.old_line_id or rec.order_id.parent_id:
        if date_today <= 5:
          if rec.date_end and rec.date_end < month_pre:
            raise ValidationError(
              f'Giá trị ngày kết thúc phải lớn hơn {month_pre.strftime("%d/%m/%Y")}')
        else:
          if rec.date_end and rec.date_end < month_current:
            raise ValidationError(
              f'Giá trị ngày kết thúc phải lớn hơn {month_current.strftime("%d/%m/%Y")}')

  @api.onchange('date_start')
  def onchange_date_start(self):
    if not self.employee_id or not self.employee_id.en_date_start:
      self.date_start = False
    if self.employee_id and self.employee_id and self.employee_id.en_date_start and self.date_start and self.date_start < self.employee_id.en_date_start:
      self.date_start = False

  date_end = fields.Date(string='Thời gian kết thúc', required=True, index=True)
  workload = fields.Float(string='Workload', default=0, required=False,
                          readonly=False, compute='_compute_en_md_workload',
                          store=True)

  @api.onchange('date_start', 'date_end')
  def _constrains_date_start(self):
    for rec in self:
      expt_txt = ''
      for resource in rec.order_id.project_id.en_resource_id.order_line.filtered(
          lambda x: x.employee_id == rec.employee_id):
        if (rec.date_start and rec.date_start < resource.date_start) or (
            rec.date_end and rec.date_end > resource.date_end):
          expt_txt = f'Thời gian bắt đầu không được nằm ngoài thời gian trong KHNL'
        else:
          expt_txt = ''
      if expt_txt:
        self.env.user.notify_warning(expt_txt, 'Cảnh báo')

  @api.onchange('date_start')
  def _onchange_date_start(self):
    if self.date_start and self.date_end and self.date_start > self.date_end:
      return {'warning': {
        'title': 'Cảnh báo',
        'message': f'Thời gian kết thúc sử dụng nguồn lực {self.employee_id.display_name} không thể nhỏ hơn thời gian bắt đầu là {self.date_start.strftime("%d/%m/%Y")}.'
      }}

  hours_indate = fields.Float(string='Số giờ làm việc của nhân viên',
                              compute_sudo=True,
                              compute='_compute_hours_indate', store=True)

  @api.depends('employee_id', 'date_start', 'date_end')
  def _compute_hours_indate(self):
    for rec in self:
      if not rec.employee_id or not rec.date_start or not rec.date_end:
        rec.hours_indate = 0
        continue
      date_from = min([rec.date_start, rec.date_end])
      date_to = max([rec.date_start, rec.date_end])
      datetime_from = datetime.combine(date_from, time.min)
      datetime_to = datetime.combine(date_to, time.max)
      employee = rec.employee_id
      hours_indate = self.env['en.technical.model'].convert_daterange_to_hours(
        employee, datetime_from, datetime_to)
      rec.hours_indate = hours_indate

  en_mh = fields.Float(string='MH', compute_sudo=True, compute='_compute_en_mh',
                       store=True)

  @api.depends('hours_indate', 'workload')
  def _compute_en_mh(self):
    for rec in self:
      rec.en_mh = rec.hours_indate * rec.workload

  en_md = fields.Float(string='MD', compute_sudo=True, readonly=False,
                       compute='_compute_en_m_uom', store=True)

  @api.depends('hours_indate', 'workload', 'employee_id')
  def _compute_en_m_uom(self):
    for rec in self:
      en_mh = 0
      if not rec.employee_id or not rec.date_start or not rec.date_end:
        rec.en_md = en_mh
        rec.en_mh = 0
        continue
      employee = rec.employee_id
      en_mh = rec.hours_indate
      rec.en_md = en_mh / employee.resource_calendar_id.hours_per_day * rec.workload
      rec.en_mh = en_mh * rec.workload

  @api.depends('hours_indate', 'en_md')
  def _compute_en_md_workload(self):
    for rec in self:
      if not rec.employee_id or not rec.date_start or not rec.date_end:
        rec.workload = 0
        continue
      employee = rec.employee_id
      en_md = rec.hours_indate
      rec.workload = (
                           rec.en_md * employee.resource_calendar_id.hours_per_day) / en_md if en_md else 0

  en_state = fields.Selection(string='Trạng thái',
                              related='employee_id.en_status')

  def read(self, fields=None, load='_classic_read'):
    self.filtered(lambda d: d.order_id.state not in ['approved',
                                                     'expire'])._compute_hours_indate()
    return super().read(fields, load)

  def convert_daterange_to_data(self, employee, start_date, end_date):
    query = f"""
        with rd as (
            select date_start, date_end, workload, state
            from en_quality_detail
            JOIN en_quality_control on en_quality_detail.order_id = en_quality_control.id
            where employee_id = {employee.id} and en_quality_control.state = 'approved'
        )
        SELECT d.date as date, sum(workload) workload
        FROM en_technical_date d
        LEFT JOIN rd on d.date between rd.date_start and rd.date_end
        WHERE d.date >= '{start_date}' and d.date <= '{end_date}'
        group by d.date
        """
    self.env.cr.execute(query)
    result = {x.get('date'): x.get('workload') or 0 for x in
              self.env.cr.dictfetchall()}
    return result

  @api.model_create_multi
  def create(self, vals_list):
    # Handle both single record and batch creation
    if not isinstance(vals_list, list):
      vals_list = [vals_list]

    for values in vals_list:
      if self._context.get(
          'import_file') and 'workload' not in values and values.get(
          'en_md') and values.get('employee_id'):
        employee = self.env['hr.employee'].browse(values.get('employee_id'))
        date_from = min([fields.Date.from_string(values.get('date_start')),
                         fields.Date.from_string(values.get('date_end'))])
        date_to = max([fields.Date.from_string(values.get('date_start')),
                       fields.Date.from_string(values.get('date_end'))])
        en_md = self.env['en.technical.model'].convert_daterange_to_hours(
          employee, date_from, date_to)
        values['workload'] = (values.get(
          'en_md') * employee.resource_calendar_id.hours_per_day) / en_md if en_md else 0
    return super().create(vals_list)

  def unlink(self):
    for rec in self:
      if rec.old_line_id:
        raise UserError(f"Không thể xóa bản ghi này !")
    return super().unlink()

  @api.onchange('employee_id', 'date_start', 'date_end', 'workload')
  def _change_date_overload(self):
    lg = self.env['res.lang']._lang_get(self.env.user.lang) or get_lang(
      self.env)
    for rec in self:
      employee = rec.employee_id
      if not employee or not employee.en_internal_ok or not rec.date_start or not rec.date_end or not rec.workload:
        continue
      datetime_start = datetime.combine(rec.date_start, time.min)
      datetime_end = datetime.combine(rec.date_end, time.max)
      if datetime_start > datetime_end:
        continue
      groupby_overwork = []
      for date_step in date_utils.date_range(datetime_start, datetime_end,
                                             relativedelta(days=1)):
        detail_domain = [('employee_id', '=', employee.id),
                         ('date_start', '<=', date_step.date()),
                         ('date_end', '>=', date_step.date())]
        if round(sum(rec.order_id.order_line.filtered(
            lambda x: x.employee_id == employee and (x._origin.id or type(
                x.id) == NewId and x.id.ref) and x.date_start <= date_step.date() and x.date_end >= date_step.date()).mapped(
            'workload')) + sum(self.env['en.quality.detail'].search(
            [('order_id.state', '=', 'approved'), ('order_id.project_id', '!=',
                                                   rec.order_id.project_id.id)] + detail_domain).mapped(
            'workload')), 10) <= 1.2:
          continue
        groupby_overwork += [date_step.date()]
      if not groupby_overwork:
        continue
      employee_txt = f'Nhân viên {employee.display_name} đã bị quá workload vào ngày'
      dated = sorted(groupby_overwork)
      dated_txt = []
      min_dated = dated[0]
      max_dated = dated[0]
      for d in dated:
        if max_dated == d or max_dated + relativedelta(days=1) == d:
          max_dated = d
          continue
        if min_dated == max_dated:
          dated_txt += [f'{max_dated.strftime(lg.date_format)}']
        else:
          dated_txt += [
            f'{min_dated.strftime(lg.date_format)} → {max_dated.strftime(lg.date_format)}']
        min_dated = d
        max_dated = d
      else:
        if min_dated == max_dated:
          dated_txt += [f'{max_dated.strftime(lg.date_format)}']
        else:
          dated_txt += [
            f'{min_dated.strftime(lg.date_format)} → {max_dated.strftime(lg.date_format)}']
      expt_txt = f'{employee_txt} {" và ".join(dated_txt)}'
      self.env.user.notify_warning(expt_txt, 'Cảnh báo')
