from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools.safe_eval import safe_eval
from odoo.tools.misc import clean_context


class ApproveRole(models.Model):
  _name = "en.approve.role"
  _description = "Vai trò phê duyệt"

  name = fields.Char(string="Vai trò", required=True)
  user_ids = fields.Many2many(string='Người dùng', comodel_name='res.users')


class ApproveFlow(models.Model):
  _name = "en.approve.flow"
  _description = "Quy trình phê duyệt"

  name = fields.Char(string="Tên quy trình", required=True)
  model_id = fields.Many2one(comodel_name="ir.model", string="Loại chứng từ",
                             required=True, ondelete='cascade',
                             domain="[('field_id.name','=','en_approve_line_ids'), ('model', '!=', 'ngsd.approval')]")
  model = fields.Char(related='model_id.model')
  project_ids = fields.Many2many(comodel_name="project.project",
                                 string="Dự án áp dụng")
  domain = fields.Char(string="Điều kiện")
  rule_ids = fields.One2many(comodel_name="en.approve.rule",
                             inverse_name="flow_id", string="Quy tắc phê duyệt")

  @api.depends("rule_ids")
  def _compute_max_line_sequence(self):
    for rec in self:
      rec.max_line_sequence = max(rec.mapped("rule_ids.sequence") or [0]) + 1

  max_line_sequence = fields.Integer(string="Max sequence in lines",
                                     compute="_compute_max_line_sequence",
                                     store=True)

  def _normalize_visible_sequence(self, rule_ids_data, existing_rules):
    """Chuẩn hóa visible_sequence dựa trên existing_rules và rule_ids_data."""
    # Lấy tất cả visible_sequence từ existing_rules
    all_sequences = [rule.visible_sequence for rule in existing_rules]
    # Thêm các visible_sequence từ rule_ids_data
    for rule_data in rule_ids_data:
      all_sequences.append(rule_data.get('visible_sequence', 0))
    # Tạo danh sách các giá trị duy nhất, sắp xếp tăng dần
    unique_sequences = sorted(set(all_sequences))
    # Tạo ánh xạ từ giá trị gốc sang giá trị mới (tăng dần từ 1)
    sequence_mapping = {old_seq: idx + 1 for idx, old_seq in
                        enumerate(unique_sequences)}
    # Cập nhật visible_sequence trong rule_ids_data
    for rule_data in rule_ids_data:
      rule_data['visible_sequence'] = sequence_mapping.get(
        rule_data.get('visible_sequence', 0), 1)
    # Cập nhật visible_sequence cho existing_rules
    for rule in existing_rules:
      rule.visible_sequence = sequence_mapping.get(rule.visible_sequence, 1)
    return rule_ids_data

  @api.model_create_multi
  def create(self, vals_list):
    """Override create để chuẩn hóa visible_sequence."""
    # Handle both single record and batch creation
    if not isinstance(vals_list, list):
      vals_list = [vals_list]

    for vals in vals_list:
      if 'rule_ids' in vals:
        rule_ids_data = [cmd[2] for cmd in vals['rule_ids'] if cmd[0] == 0]
        if rule_ids_data:
          # Không có existing_rules khi tạo mới
          normalized_rules = self._normalize_visible_sequence(rule_ids_data,
                                                              existing_rules=
                                                              self.env[
                                                                'en.approve.rule'])
          rule_idx = 0
          new_rule_ids = []
          for cmd in vals['rule_ids']:
            if cmd[0] == 0:
              new_rule_ids.append((0, 0, normalized_rules[rule_idx]))
              rule_idx += 1
            else:
              new_rule_ids.append(cmd)
          vals['rule_ids'] = new_rule_ids
    return super().create(vals_list)

  def write(self, vals):
    """Override write để chuẩn hóa visible_sequence."""
    if 'rule_ids' in vals:
      rule_ids_data = []
      updated_rule_ids = []
      # Lấy tất cả rule_ids hiện có
      existing_rules = self.rule_ids
      for cmd in vals['rule_ids']:
        if cmd[0] == 0:  # Create new rule
          rule_ids_data.append(cmd[2])
          updated_rule_ids.append(None)  # Placeholder cho bản ghi mới
        elif cmd[0] == 1:  # Update existing rule
          rule = self.env['en.approve.rule'].browse(cmd[1])
          rule_data = {'visible_sequence': rule.visible_sequence, 'id': rule.id}
          rule_data.update(cmd[2])
          rule_ids_data.append(rule_data)
          updated_rule_ids.append(rule)
        else:
          updated_rule_ids.append(None)  # Không xử lý các lệnh khác
      if rule_ids_data:
        # Chuẩn hóa visible_sequence dựa trên existing_rules và rule_ids_data
        normalized_rules = self._normalize_visible_sequence(rule_ids_data,
                                                            existing_rules=existing_rules)
        rule_idx = 0
        new_rule_ids = []
        for cmd, updated_rule in zip(vals['rule_ids'], updated_rule_ids):
          if cmd[0] == 0:
            new_rule_ids.append((0, 0, normalized_rules[rule_idx]))
            rule_idx += 1
          elif cmd[0] == 1:
            new_rule_ids.append((1, cmd[1], {
              'visible_sequence': normalized_rules[rule_idx][
                'visible_sequence']}))
            rule_idx += 1
          else:
            new_rule_ids.append(cmd)
        vals['rule_ids'] = new_rule_ids
    return super(ApproveFlow, self).write(vals)


class ApproveRule(models.Model):
  _name = "en.approve.rule"
  _description = "Quy tắc phê duyệt"
  _order = "visible_sequence ASC"

  en_role_detail = fields.Char(string='Vai trò/Vị trí')

  flow_id = fields.Many2one(comodel_name="en.approve.flow", string="Vai trò",
                            required=True, ondelete='cascade')
  sequence = fields.Integer(
    help="Gives the sequence of this line when displaying.", default=9999)

  visible_sequence = fields.Integer("Trình tự",
                                    help="Displays the sequence of the line.")

  type = fields.Selection([('role', "Vai trò"), ('person', "Người chỉ định"), ],
                          string="Loại người duyệt")
  role_id = fields.Many2one(comodel_name="en.approve.role",
                            string="Vai trò phê duyệt")
  role_selection = fields.Selection(selection=[
    ('manager', 'Giám đốc dự án'),
    ('block', 'Giám đốc khối'),
    ('implementation', 'Giám đốc triển khai'),
    ('qa', 'QA dự án'),
    ('sale', 'Sales'),
    ('accountant', 'Kế toán'),
    ('user_id', 'Quản lý dự án'),
    ('manager_department_employee', 'Quản lý Trung tâm/Ban nhân viên'),
    ('en_supervisor_id', 'Người giám sát'),
    ('leave_manager_id', 'Người duyệt nghỉ phép'),
    ('vice_ceo', 'Phó tổng giám đốc'),
  ], string="Vai trò phê duyệt")
  user_id = fields.Many2one(comodel_name="res.users", string="Người phê duyệt")
  amount = fields.Float(string="Hạn mức nguồn lực", default=0)
  en_amount = fields.Float(string="% vượt mức", default=0)

  resource_unit = fields.Selection(string='Đơn vị so sánh',
                                   selection=[('mm', 'MM'),
                                              ('budget', 'Budget ban đầu'),
                                              ('baseline',
                                               'Baseline gần nhất')],
                                   default='mm')


class ApproveLine(models.Model):
  _name = "en.approve.line"
  _description = "Thông tin phê duyệt"

  sequence = fields.Integer(string="Trình tự", readonly=True)
  approver_user_ids = fields.Many2many(comodel_name="res.users",
                                       string="Người có thể duyệt")
  user_id = fields.Many2one(comodel_name="res.users", string="Người đã duyệt")
  date = fields.Datetime(string="Thời gian duyệt")
  state = fields.Selection([('sent', "Chờ duyệt"), ('approved', "Đã duyệt"),
                            ('refused', "Từ chối"), ], string="Trạng thái",
                           default='sent', required=True, readonly=True,
                           copy=False)

  res_id = fields.Integer(string='ID tài nguyên')
  res_model = fields.Char(string='Model tài nguyên')


class NgsdApproval(models.AbstractModel):
  _name = 'ngsd.approval'
  _inherit = ['mail.thread', 'mail.activity.mixin']
  _description = 'Phê duyệt'

  def unlink(self):
    to_approver_remove = self.env['en.current.approver']
    to_line_remove = self.env['en.approve.line']
    for rec in self:
      to_approver_remove |= self.env['en.current.approver'].search(
          [('res_model', '=', rec._name), ('res_id', '=', rec.id)])
      to_line_remove |= self.env['en.approve.line'].search(
          [('res_model', '=', rec._name), ('res_id', '=', rec.id)])
    res = super().unlink()
    to_approver_remove.sudo().unlink()
    to_line_remove.sudo().unlink()
    return res

  approve_ok = fields.Boolean(string='Có thể duyệt',
                              compute='_compute_approve_ok')

  @api.depends_context('uid')
  @api.depends('en_next_approver_ids')
  def _compute_approve_ok(self):
    for rec in self:
      rec.approve_ok = rec.en_next_approver_ids and self.env.user in rec.en_next_approver_ids

  sent_ok = fields.Boolean(string='Có thể gửi', compute='_compute_sent_ok')

  @api.depends_context('uid')
  @api.depends('create_uid')
  def _compute_sent_ok(self):
    for rec in self:
      rec.sent_ok = rec.create_uid and self.env.user == rec.create_uid

  def sent_state(self):
    return 'to_approve'

  def approved_state(self):
    return 'approved'

  def refused_state(self):
    return 'refused'

  def draft_state(self):
    return 'draft'

  def button_approved(self):
    if self.state != self.sent_state(): return
    if not self.approve_ok: return
    if self.state_change('approved'):
      self.sudo().write({'state': self.approved_state()})

      # Sau khi approved QĐTLDA auto chuyển trạng thái dự án sag đang thuc hiẹn
      if self._name == 'project.decision' and self.state == 'approved':
        for rec in self:
          if rec.project_id and rec.project_id.en_state == 'wait_for_execution':
            rec.project_id.button_en_doing()
      return True

  def button_refused(self):
    if self.state != self.sent_state(): return
    if not self.approve_ok: return
    return {
      'name': 'Lý do từ chối',
      'view_mode': 'form',
      'res_model': 'en.refuse.reason.wizard',
      'type': 'ir.actions.act_window',
      'target': 'new',
    }

  def button_sent(self):
    if self.state != self.draft_state(): return
    if not self.sent_ok: return
    en_approve_line_ids, en_next_approver_ids = self.get_en_approve_line_ids()
    if not en_approve_line_ids: raise exceptions.ValidationError(
      'Không tìm thấy quy trình duyệt tương ứng với chứng từ')
    # ---- TẠO en.current.approver cho record mới----
    for user in en_next_approver_ids:
      self.env['en.current.approver'].create({
        'res_id': self.id,
        'res_model': self._name,
        'user_id': user.id,
      })

    self.with_context(clean_context(self._context)).write({
      'en_request_user_id': self.env.user.id,
      'en_request_date': fields.Datetime.now(),
      'state': self.sent_state(),
      'en_next_approver_ids': [(6, 0, en_next_approver_ids.ids)],
      'en_approve_line_ids': [(5, 0, 0)] + en_approve_line_ids,
    })
    self.state_notify(self.get_message())
    return True

  def button_sent_1(self):
    if self.state not in ['3_waiting_suggest', '3_processing']: return
    if not self.sent_ok: return
    en_approve_line_ids, en_next_approver_ids = self.get_en_approve_line_ids()
    if not en_approve_line_ids: raise exceptions.ValidationError(
      'Không tìm thấy quy trình duyệt tương ứng với chứng từ')
    self.with_context(clean_context(self._context)).write(
        {'en_request_user_id': self.env.user.id,
         'en_request_date': fields.Datetime.now(), 'state': self.sent_state(),
         'en_next_approver_ids': [(6, 0, en_next_approver_ids.ids)],
         'en_approve_line_ids': [(5, 0, 0)] + en_approve_line_ids})
    self.state_notify(self.get_message())
    return True

  def state_notify(self, message=False):
    self.clear_caches()
    for approval in self.en_approve_line_ids.search(
        [('res_id', 'in', self.ids), ('res_model', '=', self._name)]):
      if approval.state != 'sent': continue
      self.send_notify(message, approval.approver_user_ids)
      return

  def state_change(self, approve_state):
    self = self.sudo()
    self.clear_caches()
    user = self.env.user

    # Kiểm tra xem người dùng hiện tại có trong danh sách người phê duyệt
    if user not in self.en_approve_line_ids.search([
      ('res_id', 'in', self.ids),
      ('res_model', '=', self._name)
    ]).mapped('approver_user_ids'):
      return False

    update_value = dict(state=approve_state, date=fields.Datetime.now(),
                        user_id=user.id)
    en_approve_line_ids = []
    next_approver_ids = self.env['res.users']
    approval_updated = False
    updated_approval_id = False

    # Tìm dòng phê duyệt phù hợp với người dùng hiện tại
    approvals = self.en_approve_line_ids.search([
      ('res_id', 'in', self.ids),
      ('res_model', '=', self._name)
    ], order='sequence asc')

    # Cập nhật dòng hiện tại
    for approval in approvals:
      if approval.state != 'sent' or user.id not in approval.approver_user_ids.ids:
        continue
      en_approve_line_ids = [(1, approval.id, update_value)]
      updated_approval_id = approval.id
      approval_updated = True
      break

    if not approval_updated:
      return False

    if approve_state == 'refused':
      # Khi từ chối, đặt next_approver_ids rỗng và không tìm next_sequence
      next_approver_ids = self.env['res.users']
    else:
      # Kiểm tra trạng thái của tất cả các dòng, ngoại trừ dòng vừa cập nhật
      all_approved = True
      next_sequence = False
      for approval in approvals:
        if approval.id == updated_approval_id:
          continue  # Bỏ qua dòng vừa cập nhật (coi như state = 'approved')
        if approval.state == 'sent':
          all_approved = False
          if not next_sequence or approval.sequence < next_sequence:
            next_sequence = approval.sequence

      # Nếu không phải tất cả đã approved, tìm người duyệt tiếp theo
      if not all_approved and next_sequence:
        # Lọc các dòng có sequence tiếp theo và state = 'sent' từ approvals
        next_approvals = approvals.filtered(
            lambda
                a: a.sequence == next_sequence and a.state == 'sent' and a.id != updated_approval_id
        )
        for approval in next_approvals:
          next_approver_ids |= approval.approver_user_ids

    # Cập nhật bản ghi
    self.write(dict(
        en_approve_line_ids=en_approve_line_ids,
        en_next_approver_ids=[(6, 0, next_approver_ids.ids)]
    ))

    # Gửi thông báo nếu có người duyệt tiếp theo và không bị từ chối
    if approve_state == 'approved' and next_approver_ids:
      self.state_notify(self.get_message())

    # Trả về False nếu từ chối hoặc chưa duyệt hết, True nếu tất cả approved
    return all_approved if approve_state == 'approved' else True

  def get_message(self):
    return 'Bạn có bản ghi %s cần duyệt: %s' % (
      self.env['ir.model']._get(self._name).display_name, self.display_name)

  def get_flow_domain(self):
    return [('model_id.model', '=', self._name)]

  def _check_over_bmm(self):
    if self._name != 'en.resource.planning':
      return
    total_mm = self.mm_conversion or 0.0
    bmm = float(self.en_bmm) or 0.0

    # Tính %: Tổng MM so với BMM
    percent = (total_mm / bmm) * 100 if bmm else 0.0

    if (bmm == 0.0 and total_mm > 0) or percent > 105:
      raise UserError(
          "KHNL có tổng nguồn lực vượt quá 105% BMM.\n"
          "Yêu cầu Replan KHNL trước khi gửi duyệt hoặc tạo QĐTLDA mới."
      )

  def get_en_approve_line_ids(self):
    # ckeck Tổng MM kế hoạch” lớn hơn 105% giá trị trường “BMM”
    self._check_over_bmm()

    en_approve_line_ids = []
    self.clear_caches()
    self = self.sudo()
    processes = self.env['en.approve.flow'].search(self.get_flow_domain(),
                                                   order='id desc')

    all_rules = []
    for process in processes:
      if not self.filtered_domain(safe_eval(process.domain or '[]')):
        continue

      for rule in process.rule_ids:
        approver_user_ids = self.env['res.users']

        # === BẮT ĐẦU phần điều kiện bạn đã viết ===
        if self._name == 'en.wbs' and rule.amount and rule.amount > self.planned_resource:
          continue
        if self._name == 'en.resource.planning':
          if rule.resource_unit == 'mm' and rule.amount > self.resource_total:
            continue
          if rule.resource_unit == 'budget' and rule.en_amount > self.budget_over:
            continue
          if rule.resource_unit == 'baseline' and rule.en_amount > self.baseline_over:
            continue

        if rule.type == 'role' and rule.role_selection:
          role_selection = rule.role_selection

          if role_selection == 'vice_ceo':
            if self._name != 'project.decision':
              continue
            group = self.env.ref('ngsd_base.group_approver_vice_ceo')
            approver_user_ids = group.users

          elif role_selection == 'manager_department_employee':
            # rule liên quan đến phòng ban
            department = 'employee_id.department_id'
            if self._name == 'en.overtime.plan':
              department = 'create_uid.employee_id.department_id'
            if self._name == 'en.borrow.employee':
              department = 'department_lender_id'
            approver_user_ids = self.mapped(f'{department}.manager_id.user_id')
          elif role_selection == 'leave_manager_id':
            # rule liên quan đến nhân viên
            employee = 'employee_id'
            approver_user_ids = self.mapped(f'{employee}.{role_selection}')
          elif role_selection == 'en_supervisor_id':
            # rule liên quan đến quản lý nhân viên
            if self._name == 'en.hr.overtime':
              approver_user_ids = self.en_nonproject_task_id.en_supervisor_id
            if self._name == 'en.overtime.plan':
              approver_user_ids = self.en_work_nonproject_id.en_supervisor_id
          else:
            # rule liên quan đến dự án
            if role_selection != 'user_id':
              role_selection = f'en_project_{role_selection}_id'
            project = 'project_id'
            if self._name == 'en.hr.overtime':
              project = 'task_id.project_id'
            if self._name == 'en.overtime.plan':
              project = 'en_work_id.project_id'
            approver_user_ids = self.mapped(f'{project}.{role_selection}')
        elif rule.type == 'person':
          approver_user_ids = rule.user_id
        # === KẾT THÚC phần điều kiện bạn đã viết ===

        if not approver_user_ids:
          continue

        all_rules.append((rule.visible_sequence, rule, approver_user_ids))
      break  # chỉ lấy process đầu tiên hợp lệ

    if not all_rules:
      return [], self.env['res.users']

    # Tìm sequence nhỏ nhất
    min_sequence = min(r[0] for r in all_rules)

    en_next_approver_ids = self.env['res.users']
    for sequence, rule, approver_user_ids in all_rules:
      en_approve_line_ids.append((0, 0, {
        'res_model': self._name,
        'res_id': self.id,
        'sequence': rule.visible_sequence,
        'state': 'sent',
        'approver_user_ids': [(6, 0, approver_user_ids.ids)],
      }))
      # Gom tất cả approver có sequence nhỏ nhất
      if sequence == min_sequence:
        en_next_approver_ids |= approver_user_ids

    return en_approve_line_ids, en_next_approver_ids

  en_approve_line_ids = fields.One2many(string='Thông tin phê duyệt',
                                        comodel_name='en.approve.line',
                                        inverse_name='res_id',
                                        domain=lambda self: [
                                          ('res_model', '=', self._name)],
                                        readonly=True)
  en_request_user_id = fields.Many2one(string='Người gửi duyệt',
                                       comodel_name='res.users', copy=False,
                                       readonly=True)
  en_request_date = fields.Datetime(string='Ngày gửi duyệt', copy=False,
                                    readonly=True)
  en_next_approver_ids = fields.Many2many(string='Người duyệt tiếp theo',
                                          comodel_name='res.users',
                                          compute='_compute_en_next_approver_ids',
                                          inverse='_inverse_en_next_approver_ids',
                                          search='_search_en_next_approver_ids',
                                          readonly=True)

  def _compute_en_next_approver_ids(self):
    for rec in self:
      rec.en_next_approver_ids = self.env['en.current.approver'].search(
          [('res_id', '=', rec._origin.id),
           ('res_model', '=', rec._name)]).mapped('user_id')

  last_approver_id = fields.Many2one(string='Người duyệt gần nhất',
                                     comodel_name='res.users',
                                     compute='_compute_last_approver')
  last_approver_date = fields.Datetime(string='Thời gian duyệt gần nhất',
                                       compute='_compute_last_approver')

  @api.depends('en_approve_line_ids')
  def _compute_last_approver(self):
    for rec in self:
      last_line = rec.en_approve_line_ids.filtered(
        lambda l: l.state == 'approved')[-1:]
      rec.last_approver_id = last_line.user_id
      rec.last_approver_date = last_line.date

  def _search_en_next_approver_ids(self, operator, operand):
    return [('en_last_approver_ids', 'in',
             self.env['en.current.approver'].sudo()._search(
                 [('user_id', operator, operand)]))]

  def _inverse_en_next_approver_ids(self):
    new_members = []
    outdated = self.env['en.current.approver']
    for rec in self:
      current_members = rec.en_last_approver_ids
      users = rec.en_next_approver_ids
      users_new = users - current_members.user_id

      new_members += [{
        'res_id': rec.id,
        'res_model': rec._name,
        'user_id': user.id,
      } for user in users_new]
      outdated += current_members.filtered(lambda m: m.user_id not in users)

    if new_members:
      self.env['en.current.approver'].sudo().create(new_members)
    if outdated:
      outdated.sudo().unlink()

  en_last_approver_ids = fields.One2many(string='Người duyệt gần nhất',
                                         comodel_name='en.current.approver',
                                         inverse_name='res_id',
                                         domain=lambda self: [
                                           ('res_model', '=', self._name)])


class CurrentApprover(models.Model):
  _name = 'en.current.approver'
  _description = 'Người duyệt tiếp theo'

  res_id = fields.Integer(string='ID tài nguyên')
  res_model = fields.Char(string='Model tài nguyên')
  user_id = fields.Many2one(string='Người duyệt tiếp theo',
                            comodel_name='res.users')


class RefuseReason(models.TransientModel):
  _name = "en.refuse.reason.wizard"
  _description = "Lý do từ chối"

  name = fields.Char(string="Lý do từ chối", required=True)

  def do(self):
    self = self.sudo()
    model = self._context.get("active_model")
    records = self.env[model].browse(self._context.get('active_ids'))
    for record in records:
      # message = f"{self.env.user.name} đã từ chối {self.env['ir.model']._get(record._name).display_name} {record.display_name}! Lý do từ chối: {self.name}"
      if record.state_change('refused'):
        if record._name in ['en.resource.planning', 'en.quality.control']:
          record.sudo().write(dict(state='refused', reason=self.name))
        else:
          record.sudo().write(dict(state=record.refused_state()))
          if hasattr(record, '_callback_reason_refused'):
            getattr(record, '_callback_reason_refused')(self.name)
        record.sudo().message_post(
          body=f'{self.env.user.name} đã từ chối vào {fields.Datetime.now().strftime("%d-%m-%Y %H:%M:%S")}! Lý do từ chối: {self.name}')
        # record.send_notify(message, record.user_id)
        if hasattr(record, '_callback_after_refused'):
          record._callback_after_refused()
    return {
      'effect': {
        'fadeout': 'slow',
        'message': 'Đã từ chối!',
        'img_url': '/web/image/%s/%s/image_1024' % (self.env.user._name,
                                                    self.env.user.id) if self.env.user.image_1024 else '/web/static/src/img/smile.svg',
        'type': 'rainbow_man',
      }
    }
