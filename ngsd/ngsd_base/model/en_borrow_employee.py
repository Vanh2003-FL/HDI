from odoo import api, fields, models
from odoo.exceptions import ValidationError

READONLY_STATES = {
  'to_approve': [('readonly', True)],
  'approved': [('readonly', True)],
  'refused': [('readonly', True)],
  'expire': [('readonly', True)],
}


class EnBorrowEmployee(models.Model):
  _name = 'en.borrow.employee'
  _description = 'Mượn nhân sự'
  _inherit = 'ngsd.approval'
  _rec_name = 'code'

  name = fields.Char('Tên phiếu', required=True)
  borrower_id = fields.Many2one('res.users', 'Người đi mượn',
                                default=lambda self: self.env.uid)
  department_borrower_id = fields.Many2one('hr.department', 'Trung tâm đi mượn',
                                           compute=False, store=True,
                                           readonly=False,
                                           domain="[('id', 'in', department_borrower_domain)]")
  department_borrower_domain = fields.Many2many('hr.department',
                                                'Trung tâm đi mượn',
                                                compute='_get_department_borrower_domain')
  lender_id = fields.Many2one('hr.employee', 'Người cho mượn',
                              related='department_lender_id.manager_id')
  department_lender_id = fields.Many2one('hr.department',
                                         string='Trung tâm cho mượn',
                                         required=True,
                                         domain="[('id', 'in', department_lender_ids)]")
  department_lender_ids = fields.Many2many('hr.department',
                                           string='Domain Trung tâm cho mượn',
                                           default=lambda
                                               self: self._compute_department_ids())
  state = fields.Selection(string="Trạng thái", selection=[
    ('draft', 'Dự kiến'),
    ('to_approve', 'Chờ duyệt'),
    ('approved', 'Đã duyệt'),
    ('refused', 'Từ chối'),
    ('cancel', 'Hủy'),
  ], required=False, default='draft')
  approver_id = fields.Many2one(string='Người phê duyệt',
                                comodel_name='res.users')
  date = fields.Date('Ngày mượn', default=fields.Date.today(), required=True)
  code = fields.Char('Mã phiếu')
  borrow_employee_detail_ids = fields.One2many('en.borrow.employee.detail',
                                               'borrow_employee_id',
                                               string='Chi tiết mượn nhân sự')
  count_bill_borrow = fields.Integer('Nhân sự đi mượn',
                                     compute='_compute_count_bill_borrow')
  lender_employee_ids = fields.One2many('en.lender.employee',
                                        'borrow_employee_id',
                                        string='Danh sách mượn nhân sự')
  is_borrower = fields.Boolean(compute='_compute_check_borrower')
  is_lender = fields.Boolean(compute='_compute_check_lender')

  @api.depends('borrower_id')
  def _compute_check_borrower(self):
    for rec in self:
      rec.is_borrower = False
      if rec.borrower_id == self.env.user:
        rec.is_borrower = True

  @api.depends('lender_id')
  def _compute_check_lender(self):
    for rec in self:
      rec.is_lender = False
      if rec.lender_id == self.env.user.employee_id:
        rec.is_lender = True

  @api.depends('lender_employee_ids')
  def _compute_count_bill_borrow(self):
    for rec in self:
      count_number = 0
      if rec.lender_employee_ids:
        count_number = len(rec.lender_employee_ids)
      rec.count_bill_borrow = count_number

  def to_folder(self):
    if not self.count_bill_borrow:
      raise ValidationError('Phiếu mượn chưa có danh sách mượn nhân sự!')
    return {
      'name': 'Danh sách mượn nhân sự',
      'type': 'ir.actions.act_window',
      'view_mode': 'tree',
      'views': [(False, 'tree'), (False, 'form')],
      'res_model': 'en.lender.employee',
      'target': 'current',
      'domain': [('borrow_employee_id', '=', self.id)],
      'context': {
        'default_borrow_employee_id': self.id,
        'create': 0
      }
    }

  def _compute_department_ids(self):
    department_ids = self.env['hr.department'].search(
        [('id', '!=', self.env.user.employee_id.department_id.id)]).ids
    return [(6, 0, department_ids)]

  @api.onchange('borrower_id')
  def _onchange_borrower_id(self):
    if not self.borrower_id:
      self.department_borrower_id = False
    elif self.department_borrower_id not in self.department_borrower_domain:
      self.department_borrower_id = self.department_borrower_domain[:1]

  @api.depends('borrower_id')
  def _get_department_borrower_domain(self):
    for rec in self:
      department = False
      if rec.borrower_id.employee_id:
        department = self.env['hr.department'].search(
            ['|', ('manager_id', '=', rec.borrower_id.employee_id.id),
             ('deputy_manager_id', '=', rec.borrower_id.employee_id.id)])
      rec.department_borrower_domain = department

  def button_cancel(self):
    self.state = 'cancel'

  def button_to_approve(self):
    rslt = self.button_sent()
    if not rslt: return
    if self.approver_id: self.send_notify(
      f'Bạn có phiếu mượn {self.display_name} cần được duyệt', self.approver_id)
    self.write({'state': 'to_approve'})

  def new_lender_employee(self):
    return self.open_form_or_tree_view('ngsd_base.en_lender_employee_act',
                                       False, False,
                                       {'default_date': fields.Date.today(),
                                        'default_borrow_employee_id': self.id},
                                       'Tạo danh sách', 'current')

  @api.model_create_multi
  def create(self, vals_list):
    # Handle both single record and batch creation
    if not isinstance(vals_list, list):
      vals_list = [vals_list]

    for values in vals_list:
      if 'code' not in values or not values['code']:
        values['code'] = self.env['ir.sequence'].next_by_code(
          'code.borrow.employee')
    return super().create(vals_list)

  def unlink(self):
    if any(rec.state != 'draft' for rec in self):
      raise ValidationError('Chỉ được xóa bản ghi ở trạng thái Dự kiến')
    return super(EnBorrowEmployee, self).unlink()


class EnBorrowEmployeeDetail(models.Model):
  _name = 'en.borrow.employee.detail'
  _description = 'Chi tiết mượn nhân sự'

  job_position_id = fields.Many2one('en.job.position', 'Vị trí', required=True)
  level_id = fields.Many2one('en.name.level', 'Cấp bậc', required=True)
  date_start = fields.Date('Ngày bắt đầu', default=fields.Date.today(),
                           required=True)
  date_end = fields.Date('Ngày kết thúc', required=True)
  workload = fields.Float('Workload', required=True)
  description = fields.Text('Mô tả chi tiết')
  borrow_employee_id = fields.Many2one('en.borrow.employee', 'Mượn nhân sự',
                                       ondelete='cascade')

  @api.constrains('date_start', 'date_end')
  def _constrains_date_start_end(self):
    for rec in self:
      if rec.date_start and rec.date_end and rec.date_start > rec.date_end:
        raise ValidationError('Ngày bắt đầu không được lớn hơn ngày kết thúc')

  @api.constrains('workload')
  def _constrains_workload(self):
    for rec in self:
      if rec.workload <= 0 or rec.workload > 1:
        raise ValidationError('Workload phải nằm trong khoảng từ 1 đến 100%')

  def button_en_copy(self):
    return self.copy()
