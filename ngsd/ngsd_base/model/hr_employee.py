from odoo import fields, models, api, exceptions, _
from odoo.exceptions import UserError
from datetime import datetime, date, time, timedelta
from odoo.tools import config, date_utils, get_lang, html2plaintext
from pytz import timezone, UTC
from dateutil.relativedelta import relativedelta
from odoo.osv import expression
import logging
from dateutil import tz
import datetime as dt

log = logging.getLogger(__name__)


def daterange(start_date, end_date):
  for n in range(int(((end_date + timedelta(days=1)) - start_date).days)):
    yield start_date + timedelta(n)


class EmployeeCategory(models.Model):
  _inherit = 'hr.employee.category'

  day_auto_apply = fields.Integer(string='Số ngày tối thiểu', default=0)

  def cron_auto_apply(self):
    today = fields.Date.Date.context_today(self)
    for rec in self.search([], order='day_auto_apply asc'):
      start_date = today - relativedelta(days=rec.day_auto_apply)
      employees = self.env['hr.employee'].search(
          [('official_working_day', '<=', start_date)])
      # employees.write({'category_ids': [(4, rec.id)]})
      employees.write({'category_ids': [(6, 0, rec.ids)]})
      employees_remove = self.env['hr.employee'].search(
          [('active', '=', False), ('category_ids', '=', rec.id)])
      # employees_remove |= self.env['hr.employee'].search([('en_date_start', '>', start_date)])
      employees_remove.write({'category_ids': [(3, rec.id)]})


class HrDepartment(models.Model):
  _inherit = 'hr.department'

  en_os = fields.Boolean(string='OS', default=False)
  block_id = fields.Many2one('en.name.block', string='Khối', required=False)
  deputy_manager_id = fields.Many2one(string='Phó GĐ Khối NDU',
                                      comodel_name='hr.employee')
  en_project_manager_id = fields.Many2one(string='Giám đốc dự án',
                                          comodel_name='res.users')
  name = fields.Char(string='Tên Trung tâm/Ban')
  code = fields.Char(string='Mã Trung tâm/Ban')
  hr_employee_ids = fields.One2many(comodel_name='hr.employee',
                                    string='Nhân viên',
                                    inverse_name='department_id')
  count_hr_employee_ids = fields.Integer(
    string='Số lượng nhân viên trong Trung tâm/Ban',
    compute='compute_count_hr_employee_ids')
  en_department_ids = fields.One2many(comodel_name='en.department',
                                      inverse_name='department_id',
                                      string='Phòng')
  bod = fields.Boolean(default=False, string='BOD')

  employee_borrow_ids = fields.One2many('en.department.resource',
                                        'borrow_department_id', 'Nhân sự mượn',
                                        domain=[('state', '=', 'active')])
  employee_lender_ids = fields.One2many('en.department.resource',
                                        'department_id', 'Nhân sự cho mượn',
                                        domain=[('state', '=', 'active')])
  employee_lender_report_ids = fields.One2many('en.department.resource',
                                               'department_id',
                                               'Nhân sự cho mượn', )

  no_check_lender = fields.Boolean('Không cần mượn NS')
  is_support = fields.Boolean('Hỗ trợ')

  @api.depends('hr_employee_ids')
  def compute_count_hr_employee_ids(self):
    for rec in self:
      rec.count_hr_employee_ids = len(rec.hr_employee_ids)

  @api.model
  def _name_search(self, name, args=None, operator='ilike', limit=100,
      name_get_uid=None):
    args = args or []
    domain = []
    if name:
      domain = ['|', ('name', operator, name), ('code', operator, name)]
    department = self._search(domain + args, limit=limit,
                              access_rights_uid=name_get_uid)
    return department

  def unlink(self):
    list_en_department = [rec.name for rec in self if any(
        en_department.department_id for en_department in rec.en_department_ids)]
    list_project_name = [rec.name for rec in self if
                         self.env['project.project'].search(
                             [('en_department_id', '=', rec.id)])]
    if list_en_department and list_project_name:
      raise UserError(
        f"Trung tâm/ban {','.join(list_en_department)} đang có Phòng gắn với nó, vui lòng kiểm tra lại!\nTrung tâm/ban {','.join(list_project_name)} đang có Dự án gắn với nó, vui lòng kiểm tra lại!")
    elif list_en_department:
      raise UserError(
        f"Trung tâm/ban {','.join(list_en_department)} đang có Phòng gắn với nó, vui lòng kiểm tra lại!")
    elif list_project_name:
      raise UserError(
        f"Trung tâm/ban {','.join(list_project_name)} đang có Dự án gắn với nó, vui lòng kiểm tra lại!")
    return super().unlink()


class CalendarLeaves(models.Model):
  _inherit = 'resource.calendar.leaves'

  is_holiday = fields.Boolean(string='Nghỉ lễ', default=False)
  date_from_convert = fields.Date(compute='_compute_convert_date_from',
                                  store=True)
  date_to_convert = fields.Date(compute='_compute_convert_date_to', store=True)

  def write(self, vals):
    date_from, date_to, calendar_id = vals.get('date_from'), vals.get(
      'date_to'), vals.get('calendar_id')
    global_time_off_updated = self.env['resource.calendar.leaves']
    if date_from or date_to or 'calendar_id' in vals:
      global_time_off_updated = self.filtered(
        lambda r: (date_from is not None and r.date_from != date_from) or (
              date_to is not None and r.date_to != date_to) or (
                        calendar_id is not None and r.calendar_id.id != calendar_id))
      timesheets = global_time_off_updated.sudo().timesheet_ids
      if timesheets:
        timesheets.with_context(no_constrains=True).write(
            {'global_leave_id': False, 'en_state': 'new'})
        timesheets.with_context(no_constrains=True).unlink()
    result = super(CalendarLeaves, self).write(vals)
    if global_time_off_updated:
      global_time_offs_with_leave_timesheet = global_time_off_updated.filtered(
        lambda
            r: not r.resource_id and r.calendar_id.company_id.internal_project_id and r.calendar_id.company_id.leave_timesheet_task_id)
      global_time_offs_with_leave_timesheet.with_context(
        no_constrains=True).sudo()._timesheet_create_lines()
    return result

  @api.depends('date_from')
  def _compute_convert_date_from(self):
    for rec in self:
      date_from_convert = False
      if rec.date_from:
        date_from_convert = (rec.date_from + relativedelta(hours=7)).date()
      rec.date_from_convert = date_from_convert

  @api.depends('date_to')
  def _compute_convert_date_to(self):
    for rec in self:
      date_to_convert = False
      if rec.date_to:
        date_to_convert = (rec.date_to + relativedelta(hours=7)).date()
      rec.date_to_convert = date_to_convert

  def get_domain_tech(self, check_holiday=True):
    domain_list = []
    for rec in self:
      if check_holiday and not rec.is_holiday:
        continue
      date_from = (rec.date_from + relativedelta(hours=7)).date()
      date_to = (rec.date_to + relativedelta(hours=7)).date()

      domain = [('date', '>=', date_from), ('date', '<=', date_to)]
      if rec.resource_id:
        domain.append(
            ('employee_id', '=', rec.resource_id.user_id.employee_id.id))
      domain_list.append(domain)
    return domain_list

  @api.model_create_multi
  def create(self, vals_list):
    leaves = super(CalendarLeaves, self).create(vals_list)
    tech_domains = leaves.get_domain_tech(check_holiday=False)
    self.recompute_technumber_by_domain(tech_domains)
    return leaves

  def write(self, vals):
    is_date_change = vals.get('date_from') or vals.get('date_to')
    tech_domains = []
    if is_date_change:
      tech_domains = self.get_domain_tech()

    result = super(CalendarLeaves, self).write(vals)

    if is_date_change:
      tech_domains += self.get_domain_tech()

    self.recompute_technumber_by_domain(tech_domains)
    return result

  # Todo: Bỏ hàm này dùng sang hàm dưới
  def recompute_technumber(self, date_list):
    if not date_list:
      return
    need_recomputes = self.env['en.technical.model']
    for date_l in date_list:
      need_recomputes |= self.env['en.technical.model'].search(
          [('date', '>=', date_l[0]), ('date', '<=', date_l[1])])
    need_recomputes._compute_technumber()

  def recompute_technumber_by_domain(self, domain_list):
    need_recomputes = self.env['en.technical.model']
    for domain in domain_list:
      need_recomputes |= self.env['en.technical.model'].search(domain)
    need_recomputes and need_recomputes._compute_technumber()

  def unlink(self):
    tech_domains = self.get_domain_tech(False)
    res = super().unlink()
    self.recompute_technumber_by_domain(tech_domains)

    return res

  def _timesheet_prepare_line_values(self, index, employee_id, work_hours_data,
      day_date, work_hours_count):
    self.ensure_one()
    return {
      'name': _("Time Off (%s/%s)", index + 1, len(work_hours_data)),
      'project_id': employee_id.company_id.sudo().internal_project_id.id,
      'task_id': employee_id.company_id.sudo().leave_timesheet_task_id.id,
      'account_id': employee_id.company_id.sudo().internal_project_id.analytic_account_id.id,
      'unit_amount': work_hours_count,
      'user_id': employee_id.user_id.id,
      'date': day_date,
      'global_leave_id': self.id,
      'employee_id': employee_id.id,
      'company_id': employee_id.company_id.id,
    }


class TechnicalDate(models.Model):
  _name = 'en.technical.date'

  date = fields.Date(string='Ngày', index=True, required=1)

  def auto_create_technical_compute(self):
    start_date = date(2020, 1, 1)
    end_date = date(2030, 12, 31)
    tech_sudo = self.sudo()
    tech_sudo.search([]).unlink()
    vals_list = []
    for d in daterange(start_date, end_date):
      vals_list.append({'date': d})
    tech_sudo.create(vals_list)


class TechnicalModel(models.Model):
  _name = 'en.technical.model'

  employee_id = fields.Many2one(string='🚑', comodel_name='hr.employee',
                                index=True)
  date = fields.Date(string='🚑', index=True)
  tech = fields.Char(string='🚑', compute_sudo=True,
                     compute='_compute_technumber', store=True)
  tech_type = fields.Char(string='🚑', compute_sudo=True,
                          compute='_compute_technumber',
                          help='Phân biệt xem nhân viên có làm việc hay không',
                          store=True)
  number = fields.Float(string='🚑', compute_sudo=True,
                        compute='_compute_technumber', store=True)

  @api.depends('employee_id', 'date', 'employee_id.tz',
               'employee_id.en_date_start', 'employee_id.departure_date',
               'employee_id.en_day_layoff_from', 'employee_id.en_day_layoff_to')
  def _compute_technumber(self):
    for rec in self:
      employee = rec.employee_id
      tz = rec.employee_id.tz
      calendar = employee.resource_calendar_id
      if not employee or not calendar or not rec.date:
        rec.tech = ''
        rec.number = 0
        continue
      date = rec.date
      comparedtime_from = timezone(tz).localize(
        datetime.combine(date, time.min)).astimezone(timezone('UTC')).replace(
        tzinfo=None)
      comparedtime_to = timezone(tz).localize(
        datetime.combine(date, time.max)).astimezone(timezone('UTC')).replace(
        tzinfo=None)
      workhours = calendar.get_work_hours_count(comparedtime_from,
                                                comparedtime_to,
                                                compute_leaves=False)
      if not workhours:
        # không phải ngày làm việc
        rec.tech = 'off'
        rec.tech_type = 'off'
        rec.number = 0
        continue
      if not rec.employee_id.en_date_start:
        # Không có ngày bắt đầu
        rec.tech = 'leave'
        rec.tech_type = 'not_work'
        rec.number = 0
        continue
      if rec.employee_id.departure_date and rec.employee_id.departure_date <= rec.date:
        # Nghỉ việc
        rec.tech = 'leave'
        rec.tech_type = 'not_work'
        rec.number = 0
        continue
      if rec.employee_id.en_date_start > rec.date:
        # chưa đi làm
        rec.tech = 'leave'
        rec.tech_type = 'not_work'
        rec.number = 0
        continue
      if rec.employee_id.en_day_layoff_from and rec.employee_id.en_day_layoff_to and rec.employee_id.en_day_layoff_from <= rec.date <= rec.employee_id.en_day_layoff_to:
        # trong khoảng bị nghỉ việc/nghỉ thai sản
        rec.tech = 'leave'
        rec.tech_type = 'layoff'
        rec.number = 0
        continue
      if rec.employee_id.en_day_layoff_from and not rec.employee_id.en_day_layoff_to and rec.employee_id.en_day_layoff_from <= rec.date:
        # trong khoảng bị nghỉ việc/nghỉ thai sản
        rec.tech = 'leave'
        rec.tech_type = 'layoff'
        rec.number = 0
        continue
      if not rec.employee_id.en_day_layoff_from and rec.employee_id.en_day_layoff_to and rec.date <= rec.employee_id.en_day_layoff_to:
        # trong khoảng bị nghỉ việc/nghỉ thai sản
        rec.tech = 'leave'
        rec.tech_type = 'layoff'
        rec.number = 0
        continue
      month_leave_intervals = employee.list_leaves(comparedtime_from,
                                                   comparedtime_to)
      leavehours = 0
      all_leaves = self.env['resource.calendar.leaves']
      for day, hours, leave in month_leave_intervals:
        if leave.holiday_id.holiday_status_id.code == 'W':
          continue
        leavehours += hours
        all_leaves += leave
      if leavehours:
        if all_leaves.holiday_id:
          rec.tech = 'leave'
          rec.tech_type = 'leave'
          rec.number = workhours - leavehours
        elif any(x.is_holiday for x in all_leaves):
          rec.tech = 'leave'
          rec.tech_type = 'holiday'
          rec.number = workhours - leavehours
        else:
          rec.tech = 'leave'
          rec.tech_type = 'leave_other'
          rec.number = workhours - leavehours
      else:
        rec.tech = 'work'
        rec.tech_type = 'work'
        rec.number = workhours

  def convert_daterange_to_data(self, employee, start_date, end_date):
    if start_date > end_date:
      return {}
    # data_ranges = self.daterange_to_date(start_date, end_date)
    # for d_r in data_ranges:
    #     check_query = f"""
    #     select x.c_date
    #     from ({" union ".join(["select '%s'::date as c_date"%d for d in d_r])}) x
    #     left join (SELECT date
    #     FROM en_technical_model
    #     WHERE employee_id = {employee.id} and date >= '{min(d_r)}' and date <= '{max(d_r)}') tech on tech.date = x.c_date
    #     where tech.date is null
    #     """
    #     self.env.cr.execute(check_query)
    #     missing_dates = self.env.cr.fetchall()
    #     if missing_dates:
    #         self.env['en.technical.model'].create([{'employee_id': employee.id, 'date': missing_date[0]} for missing_date in missing_dates])
    #         self.env.cr.commit()
    query = f"""
        SELECT date, tech, tech_type, number
        FROM en_technical_model
        WHERE employee_id = {employee.id} AND date >= '{start_date}' AND date <= '{end_date}'
        """
    self.env.cr.execute(query)
    res = {x.pop('date'): x for x in self.env.cr.dictfetchall()}
    return res

  def convert_daterange_to_hours(self, employee, start_date, end_date,
      exclude_tech=None,
      exclude_tech_type=['off', 'not_work', 'layoff', 'holiday']):
    if start_date > end_date:
      return 0
    exclude_tech_domain = ''
    if exclude_tech:
      exclude_tech_domain = ' AND tech not in %s' % (
        str(exclude_tech).replace('[', '(').replace(']', ')'))
    exclude_tech_type_domain = ''
    if exclude_tech_type:
      exclude_tech_type_domain = ' AND tech_type not in %s' % (
        str(exclude_tech_type).replace('[', '(').replace(']', ')'))
    query = f"""
        SELECT count(*) * 8
        FROM en_technical_model
        WHERE employee_id = {employee.id} AND date >= '{start_date}' AND date <= '{end_date}' {exclude_tech_domain} {exclude_tech_type_domain}
        """
    self.env.cr.execute(query)
    res = self.env.cr.fetchone()
    return res and res[0] or 0

  def convert_daterange_to_count(self, employee, start_date, end_date,
      exclude_tech=None,
      exclude_tech_type=['off', 'holiday', 'not_work', 'layoff']):
    if start_date > end_date:
      return 0
    exclude_tech_domain = ''
    if exclude_tech:
      exclude_tech_domain = ' AND tech not in %s' % (
        str(exclude_tech).replace('[', '(').replace(']', ')'))
    exclude_tech_type_domain = ''
    if exclude_tech_type:
      exclude_tech_type_domain = ' AND tech_type not in %s' % (
        str(exclude_tech_type).replace('[', '(').replace(']', ')'))
    query = f"""
        SELECT count(number)
        FROM en_technical_model
        WHERE employee_id = {employee.id} AND date >= '{start_date}' AND date <= '{end_date}' {exclude_tech_domain} {exclude_tech_type_domain}
        """
    self.env.cr.execute(query)
    res = self.env.cr.fetchone()
    return res and res[0] or 0

  def daterange_to_date(self, start_date, end_date):
    data_range = [d for d in daterange(start_date, end_date)]
    rate = 100
    for i in range(0, len(data_range), rate):
      yield data_range[i:i + rate]

  def auto_create_technical_compute(self, employees=None, start_date=None,
      end_date=None):
    if not employees:
      employees = self.env['hr.employee'].with_context(
        active_test=False).search([])
    if not start_date:
      start_date = datetime(2020, 1, 1, 0, 0, 0)
    if not end_date:
      end_date = datetime(2030, 12, 31, 23, 59, 59)
    i = 0
    for employee in employees:
      i += 1
      for d in date_utils.date_range(start_date, end_date,
                                     relativedelta(days=1)):
        tech = self.search_count(
            [('employee_id', '=', employee.id), ('date', '=', d.date())])
        if not tech:
          tech = self.create({'employee_id': employee.id, 'date': d.date()})
      log.info(
        f'done auto_create_technical_compute {employee} {i}/{len(employees)}')
      self.env.cr.commit()

  def manual_create_technical_compute(self, employees=None, start_date=None,
      end_date=None):
    if not employees:
      employees = self.env['hr.employee'].with_context(
        active_test=False).search([])
    if not start_date:
      start_date = datetime(2020, 1, 1, 0, 0, 0)
    if not end_date:
      end_date = datetime(2030, 12, 31, 23, 59, 59)
    i = 0
    for employee in employees:
      i += 1
      for d in date_utils.date_range(start_date, end_date,
                                     relativedelta(days=1)):
        tech = self.search_count(
            [('employee_id', '=', employee.id), ('date', '=', d.date())])
        if not tech:
          tech = self.create({'employee_id': employee.id, 'date': d.date()})
      log.info(
        f'done manual_create_technical_compute {employee} {i}/{len(employees)}')

  def count_net_working_days_by_months(self, date_start, date_end):
    """
        Đếm số ngày làm việc cho từng tháng trong khoảng date_start → date_end
        (bỏ T7, CN và ngày nghỉ lễ)
        Kết quả: {date(YYYY,MM,01): số ngày làm việc}
        """
    if not date_start or not date_end:
      return {}
    first_day_of_month = date_start.replace(day=1)
    last_day_of_month = (date_end.replace(day=1) +
                         relativedelta(months=1, days=-1))
    query = """ \
            WITH date_range \
                AS (SELECT generate_series(%s::date, %s::date, interval '1 day') ::date \
                AS day \
                ) \
               , holidays AS ( \
            SELECT DISTINCT g:: date AS day \
            FROM resource_calendar_leaves rcl, generate_series(rcl.date_from_convert, rcl.date_to_convert, interval '1 day') g \
            WHERE rcl.is_holiday = TRUE \
              AND rcl.date_to_convert >= %s:: date \
              AND rcl.date_from_convert <= %s:: date \
                ) \
            SELECT date_trunc('month', dr.day)::date AS month_start, COUNT(*) AS working_days \
            FROM date_range dr \
                     LEFT JOIN holidays h ON h.day = dr.day \
            WHERE EXTRACT(DOW FROM dr.day) NOT IN (0, 6) \
              AND h.day IS NULL \
            GROUP BY month_start \
            ORDER BY month_start; \
                """
    self.env.cr.execute(query, [str(first_day_of_month), str(last_day_of_month),
                                str(first_day_of_month),
                                str(last_day_of_month), ])
    result = self.env.cr.fetchall()
    return {str(row[0]): row[1] for row in result}


class HrEmployeeLayoff(models.TransientModel):
  _name = 'hr.employee.layoff.wizard'

  employee_id = fields.Many2one(string='Nhân viên', comodel_name='hr.employee')
  state = fields.Selection(string='Trạng thái',
                           selection=[('inactive', 'Nghỉ việc'),
                                      ('semi-inactive', 'Nghỉ không lương'),
                                      ('maternity-leave', 'Nghỉ thai sản')],
                           default='inactive', required=True)
  date = fields.Date(string='Ngày nghỉ việc')
  text = fields.Text(string='Lý do nghỉ việc')

  day_layoff_from = fields.Date(string='Ngày bắt đầu')
  day_layoff_to = fields.Date(string='Ngày kết thúc')
  text_layoff = fields.Text(string='Lý do')

  @api.onchange('date', 'employee_id', 'state')
  def onchange_departure_date(self):
    if self.state == 'inactive' and self.employee_id:
      if (not self.employee_id.en_date_start and self.date) or (
          self.employee_id.en_date_start and self.date and self.employee_id.en_date_start > self.date):
        return {'warning': {
          'title': 'Lỗi xác nhận',
          'message': 'Ngày dừng hoạt động nhân viên không thể nhỏ hơn ngày bắt đầu làm việc của nhân viên',
        }}

  @api.onchange('day_layoff_from', 'day_layoff_to', 'employee_id', 'state')
  def onchange_day_layoff_from(self):
    if self.state in ['semi-inactive', 'maternity-leave'] and self.employee_id:
      text = 'Tạm dừng'
      if self.state == 'semi-inactive':
        text = 'Nghỉ không lương'
      if self.state == 'maternity-leave':
        text = 'Nghỉ thai sản'
      if (not self.employee_id.en_date_start and self.day_layoff_from) or (
          self.employee_id.en_date_start and self.day_layoff_from and self.employee_id.en_date_start > self.day_layoff_from):
        return {'warning': {
          'title': 'Lỗi xác nhận',
          'message': f'Ngày {text} của nhân viên không thể nhỏ hơn ngày bắt đầu làm việc của nhân viên.',
        }}
      if self.day_layoff_from and self.day_layoff_to and self.day_layoff_to < self.day_layoff_from:
        return {'warning': {
          'title': 'Lỗi xác nhận',
          'message': f'Ngày kết thúc {text} của nhân viên không thể nhỏ hơn ngày bắt đầu tạm dừng của nhân viên.',
        }}
      if self.day_layoff_from and self.employee_id.departure_date and self.day_layoff_from >= self.employee_id.departure_date:
        return {'warning': {
          'title': 'Lỗi xác nhận',
          'message': f'Ngày bắt đầu {text} phải trước ngày dừng của nhân viên.',
        }}
      if self.day_layoff_to and self.employee_id.departure_date and self.day_layoff_to >= self.employee_id.departure_date:
        return {'warning': {
          'title': 'Lỗi xác nhận',
          'message': f'Ngày kết thúc {text} phải trước ngày dừng của nhân viên.',
        }}

  def do(self):
    groupby_overwork = {}
    lg = self.env['res.lang']._lang_get(self.env.user.lang) or get_lang(
      self.env)
    date_start = self.date
    date_end = self.date
    today = fields.Date.Date.context_today(self)
    if self.state != 'inactive':
      date_start = min([self.day_layoff_from, self.day_layoff_to])
      date_end = max([self.day_layoff_from, self.day_layoff_to])
    if self.state == 'inactive':
      value_departure = {
        'departure_date': self.date,
        'en_text_off': self.text,
        'rest_state': self.state
      }
      if self.date and self.date <= today:
        value_departure['en_status'] = self.state
        value_departure['active'] = False
        resource_project = self.env['resource.project'].search([
          ('employee_id', '=', self.employee_id.id),
          ('date_start', '<=', self.date),
          ('date_end', '>=', self.date)
        ])
        for record in resource_project:
          record.action_leave(self.date)
        self.employee_id.action_change_date_end(self.date)
        self.employee_id.write(value_departure)
        self.employee_id.user_id.sudo().write({'active': False})
      if self.date > today:
        self.employee_id.write(value_departure)
    else:
      text = 'Tạm dừng'
      if self.state == 'semi-inactive':
        text = 'Nghỉ không lương'
      if self.state == 'maternity-leave':
        text = 'Nghỉ thai sản'
      value_pause = {
        'en_day_layoff_from': self.day_layoff_from,
        'en_day_layoff_to': self.day_layoff_to,
        'en_date_from': self.day_layoff_from,
        'en_date_to': self.day_layoff_to,
        'en_text_layoff': self.text_layoff,
        'rest_state': self.state,
      }
      self.env['resource.calendar.leaves'].sudo().search(
          [('name', '=', _("%s: %s", self.employee_id.name, text))]).unlink()
      vals_list = [{
        'name': _("%s: %s" % (self.employee_id.name, text)),
        'date_from': timezone(self.env.user.tz or 'UTC').localize(
          datetime.combine(date_start, time.min)).astimezone(UTC).replace(
          tzinfo=None),
        'date_to': timezone(self.env.user.tz or 'UTC').localize(
          datetime.combine(date_end, time.max)).astimezone(UTC).replace(
          tzinfo=None),
        'resource_id': self.employee_id.resource_id.id,
        'calendar_id': self.employee_id.resource_calendar_id.id,
        'time_type': 'leave',
      }]
      self.env['resource.calendar.leaves'].sudo().create(vals_list)
      if self.day_layoff_from and self.day_layoff_from <= today:
        value_pause['en_status_hr'] = self.state
        if not self.employee_id.active:
          value_pause['active'] = True
        resource_project = self.env['resource.project'].search([
          ('employee_id', '=', self.employee_id.id),
          ('date_start', '<=', self.day_layoff_from),
          ('date_end', '>=', self.day_layoff_from)
        ])
        for record in resource_project:
          record.action_leave(self.day_layoff_from)
        resource_details = self.env['en.resource.detail'].search([
          ('employee_id', '=', self.employee_id.id),
          ('date_start', '<', self.day_layoff_from),
          ('date_end', '>=', self.day_layoff_from)
        ])
        for resource in resource_details:
          resource.sudo().write({
            'date_end': self.day_layoff_from - relativedelta(days=1)
          })
        self.employee_id.action_change_date_end(self.date)
        self.employee_id.write(value_pause)
      if self.day_layoff_from and self.day_layoff_from > today:
        self.employee_id.write(value_pause)
    return {'type': 'ir.actions.act_window_close'}


class HrEmployeeBase(models.AbstractModel):
  _inherit = "hr.employee.base"

  leave_manager_id = fields.Many2one(related=False, store=True)
  lock_create_timesheet = fields.Datetime(string='Ngày khóa sổ khai Timesheet',
                                          readonly=True, copy=False)
  lock_approve_timesheet = fields.Datetime(
    string='Ngày khóa sổ duyệt Timesheet', readonly=True, copy=False)
  lock_create_timesheet_exp = fields.Datetime(
    string='Hạn Ngày khóa sổ khai Timesheet', readonly=True, copy=False)
  lock_approve_timesheet_exp = fields.Datetime(
    string='Hạn Ngày khóa sổ duyệt Timesheet', readonly=True, copy=False)


class HrEmployee(models.Model):
  _inherit = 'hr.employee'

  technical_field_27774 = fields.One2many(string='🪙',
                                          comodel_name='en.resource.detail',
                                          inverse_name='employee_id')
  train_ctv = fields.Char(string='PC Đào tạo/CTV', groups='hr.group_hr_user')
  job_code_id = fields.Many2one(comodel_name='job.code', string='Job code',
                                groups='hr.group_hr_user', required=True,
                                related='job_id.job_code_id')
  level_id = fields.Many2one(comodel_name='hr.level', string='Level',
                             domain="[('parent_id','=', False)]",
                             groups='hr.group_hr_user', required=True,
                             related='job_id.level_id')
  sub_level_id = fields.Many2one(comodel_name='hr.level', string='Sub-Level',
                                 domain="[('parent_id','!=', False), ('parent_id', '=?', level_id)]",
                                 groups='hr.group_hr_user', required=True,
                                 related='job_id.sub_level_id')
  pay_grade_id = fields.Many2one(comodel_name='pay.grade', string='Pay grade',
                                 groups='hr.group_hr_manager')
  salary_grade = fields.Many2one(comodel_name='salary.grade',
                                 string='Bậc lương',
                                 groups='hr.group_hr_manager')
  official_working_day = fields.Date(string='Ngày làm việc chính thức',
                                     groups='hr.group_hr_user')
  seniority_date = fields.Char(string='Thâm niên',
                               compute='compute_seniority_date',
                               groups='hr.group_hr_user')
  rest_state = fields.Selection(
      [('inactive', 'Nghỉ việc'), ('semi-inactive', 'Nghỉ không lương'),
       ('maternity-leave', 'Nghỉ thai sản')], string='Trạng thái nghỉ',
      groups='hr.group_hr_user', compute='compute_rest_state')
  date_start_training = fields.Date(string='Ngày bắt đầu đào tạo/thực tập/CTV',
                                    groups='hr.group_hr_user')
  date_end_training = fields.Date(string='Ngày kết thúc đào tạo/thực tập/CTV',
                                  groups='hr.group_hr_user')
  date_start_probation = fields.Date(string='Ngày bắt đầu thử việc',
                                     groups='hr.group_hr_user')
  date_end_probation = fields.Date(string='Ngày kết thúc thử việc',
                                   groups='hr.group_hr_user')
  salary_gross_offer = fields.Integer(string='Lương Gross Offer',
                                      groups='hr.group_hr_user')
  salary_probation = fields.Integer(string='Lương Thử việc',
                                    groups='hr.group_hr_user')
  salary_basic = fields.Integer(string='Lương cơ bản',
                                groups='hr.group_hr_user')
  lunch_allowance = fields.Integer(string='Trợ cấp ăn trưa',
                                   groups='hr.group_hr_user')
  travel_allowance = fields.Integer(string='Trợ cấp đi lại',
                                    groups='hr.group_hr_user')
  salary_temporary_effective = fields.Integer(string='Lương hiệu quả tạm tính',
                                              groups='hr.group_hr_user')
  total_new_income = fields.Integer(string='Tổng thu nhập mới',
                                    groups='hr.group_hr_user')
  total_old_income = fields.Integer(string='Tổng thu nhập cũ',
                                    groups='hr.group_hr_user')
  pti_insurance_level = fields.Integer(string='Mức bảo hiểm PTI',
                                       groups='hr.group_hr_user')
  notebook_bhxh = fields.Char(string='Sổ BHXH', groups='hr.group_hr_user')
  tax_code = fields.Char(string='Mã số thuế', groups='hr.group_hr_user')
  date_tax = fields.Date(string='Ngày cấp MST', groups='hr.group_hr_user')
  place_tax = fields.Char(string='Nơi cấp MST', groups='hr.group_hr_user')
  depend_persion_id = fields.One2many(comodel_name='depend.persion',
                                      string='Người phụ thuộc/Quan hệ nhân thân',
                                      inverse_name='hr_employee_id',
                                      groups='hr.group_hr_user')
  regular_address = fields.Char(string='Địa chỉ thường trú',
                                groups='hr.group_hr_user', required=False)
  cccd_date = fields.Date(string='Ngày cấp CCCD', groups='hr.group_hr_user',
                          required=False)
  cccd_place = fields.Char(string='Nơi cấp CCCD', groups='hr.group_hr_user',
                           required=False)
  address_home_id = fields.Many2one(required=False)
  identification_id = fields.Char(required=False)
  birthday = fields.Date(required=False)
  gender = fields.Selection(required=False)
  parent_id = fields.Many2one(string="Quản lý trực tiếp", required=True)
  indirect_manager = fields.Many2one('hr.employee', string='Quản lý gián tiếp',
                                     groups='hr.group_hr_user')
  check_representative = fields.Boolean(string='Người đại diện',
                                        groups='hr.group_hr_user')
  address_current = fields.Char(string='Địa chỉ hiện tại', required=False,
                                groups='hr.group_hr_user')
  res_partner_bank_ids = fields.One2many(string='Ngân hàng',
                                         comodel_name='res.partner.bank',
                                         inverse_name='hr_employee_id',
                                         groups='hr.group_hr_user')
  private_email = fields.Char(readonly=False)
  state_hr_employee = fields.Selection(
      [('permanent', 'Chính thức'), ('probation', 'Thử việc'),
       ('training', 'Đào tạo'), ('inter', 'Thực tập'),
       ('maternity', 'Thai sản'), ('semi-inactive', 'Nghỉ không lương'),
       ('contract_lease', 'Thuê khoán')], string='Tình trạng',
      groups='hr.group_hr_user')
  old_state_hr_employee = fields.Char(string='Tình trạng cũ',
                                      groups='hr.group_hr_user', readonly=1,
                                      copy=False)
  shift = fields.Selection([('ca_vip', 'Ca VIP'), ('ca_thuong', 'Ca Thường'),
                            ('ca_linh_hoat', 'Ca linh hoạt')],
                           default='ca_thuong', string='Ca làm việc',
                           groups='hr.group_hr_user')
  resource_project_ids = fields.One2many(string='Danh sách nhân sự',
                                         comodel_name='resource.project',
                                         inverse_name='employee_id',
                                         groups='hr.group_hr_user')

  def button_show_history(self):
    action = {
      'type': 'ir.actions.act_window',
      'name': 'Lịch sử nhân viên',
      'res_model': 'hr.employee',
      'view_mode': 'form',
      'views': [(self.env.ref('ngsd_base.form_history_employee').id, 'form')],
      'res_id': self.id,
      'target': 'new',
      'context': {'default_message_follower_ids': self.message_follower_ids.ids,
                  'default_activity_ids': self.activity_ids.ids,
                  'default_message_ids': self.message_ids.ids},
    }
    return action

  parent_path_chart = fields.Char(
      'Path xem sơ đồ',
      compute='_compute_parent_path_chart', recursive=True, store=True,
      compute_sudo=True, groups='hr.group_hr_user'
  )

  @api.depends('en_level_id', 'en_level_id.sequence', 'parent_id',
               'parent_id.en_level_id', 'parent_id.en_level_id.sequence',
               'en_department_id', 'en_department_id.manager_id')
  def _compute_parent_path_chart(self):
    for employee in self:
      parent_path_chart = ''
      min_sequence = 1
      if employee.parent_id and employee.parent_id.en_level_id.sequence < employee.en_level_id.sequence and employee.en_department_id.manager_id != employee.parent_id:
        parent_path_chart = employee.parent_id.parent_path_chart
        min_sequence = employee.parent_id.en_level_id.sequence + 1
      if min_sequence < employee.en_level_id.sequence:
        parent_path_chart += '/'.join([''] + ['False LV' + str(i) for i in
                                              range(min_sequence,
                                                    employee.en_level_id.sequence)])
      parent_path_chart += f'/{employee.id}'
      employee.parent_path_chart = parent_path_chart

  @api.constrains('check_representative')
  def check_constrains_representative(self):
    for rec in self:
      if rec.check_representative:
        exit_representative = self.search(
            [('check_representative', '=', True), ('id', '!=', rec.id)])
        if exit_representative:
          raise UserError('Chỉ được một người là đại diện')

  @api.constrains('en_type_id', 'barcode')
  def check_constrains_barcode(self):
    for rec in self:
      if rec.en_type_id.en_internal:
        if not rec.barcode:
          raise UserError('Thiếu giá trị bắt buộc cho trường Mã nhân sự')
      if rec.barcode and self.search_count([('barcode', '=', rec.barcode)]) > 1:
        raise UserError('Mã nhân sự %s đã tồn tại' % rec.barcode)

  @api.depends('en_status_hr')
  def compute_rest_state(self):
    for rec in self:
      if rec.en_status_hr == 'inactive':
        rec.rest_state = 'inactive'
      elif rec.en_status_hr == 'semi-inactive':
        rec.rest_state = 'semi-inactive'
      elif rec.en_status_hr == 'maternity-leave':
        rec.rest_state = 'maternity-leave'
      else:
        rec.rest_state = False

  @api.depends('departure_date', 'official_working_day')
  def compute_seniority_date(self):
    for rec in self:
      if not rec.official_working_day or not isinstance(
          rec.official_working_day, date):
        rec.seniority_date = f'0 Ngày'
        continue
      else:
        if rec.departure_date:
          seniority_date = relativedelta(rec.departure_date,
                                         rec.official_working_day)
        else:
          seniority_date = relativedelta(date.today(), rec.official_working_day)
        seniority_date += relativedelta(days=1)
        rec.seniority_date = f'{seniority_date.years} Năm,{seniority_date.months} Tháng, {seniority_date.days} Ngày'

  @api.constrains('date_start_training', 'date_end_training')
  def check_date_training(self):
    if self.date_start_training and self.date_end_training and self.date_start_training > self.date_end_training:
      raise UserError('Ngày bắt đầu đào tạo phải nhỏ hơn ngày kết thúc đào tạo')

  @api.constrains('date_start_probation', 'date_end_probation')
  def check_date_probation(self):
    if self.date_end_probation and self.date_start_probation and self.date_start_probation > self.date_end_probation:
      raise UserError(
        'Ngày bắt đầu thử việc phải nhỏ hơn ngày kết thúc thử việc')

  @api.onchange('sub_level_id')
  def get_level_id(self):
    self.level_id = self.sub_level_id.parent_id

  @api.onchange('level_id')
  def get_sub_level_id(self):
    if self.sub_level_id.parent_id != self.level_id:
      self.sub_level_id = False

  def action_departure_pause_employee(self):
    utc_time = datetime.utcnow()
    to_zone = tz.gettz('Asia/Ho_Chi_Minh')
    local_time = utc_time.replace(tzinfo=dt.timezone.utc).astimezone(
      to_zone).date()
    self.action_departure_employee(local_time)
    self.action_pause_employee(local_time)

  def action_departure_employee(self, local_time):
    employee_departure = self.search([('departure_date', '=', local_time),
                                      ('en_status', 'not in', ['inactive'])])
    for employee in employee_departure:
      employee.action_departure()

  def action_departure(self):
    for employee in self:
      resource_project = self.env['resource.project'].search([
        ('employee_id', '=', employee.id),
        ('date_start', '<=', employee.departure_date),
        ('date_end', '>=', employee.departure_date)
      ])
      for resource in resource_project:
        resource.action_leave(employee.departure_date)
      employee.write({
        'en_status': 'inactive',
        'active': False,
      })
      employee.action_change_date_end(employee.departure_date)
      employee.user_id.sudo().write({'active': False})

  def action_pause_employee(self, local_time):
    employee_pause = self.search(
        [('en_day_layoff_from', '=', local_time), ('en_status', '=', 'active')])
    for employee in employee_pause:
      resource_project = self.env['resource.project'].search([
        ('employee_id', '=', employee.id),
        ('date_start', '<=', employee.en_day_layoff_from),
        ('date_end', '>=', employee.en_day_layoff_from)
      ])
      for resource in resource_project:
        resource.action_leave(employee.en_day_layoff_from)
      employee.action_change_date_end(local_time)
      employee.write({
        'en_status_hr': employee.rest_state,
      })

  def cron_create_birthday_allocation(self):
    today = fields.Date.today()
    leave_type = self.env['hr.leave.type'].search([('code', '=', 'SN')],
                                                  limit=1)
    if not leave_type:
      return
    for employee in self.search([('state_hr_employee', '=', 'permanent')]):
      if not employee.birthday:
        continue
      if employee.birthday.month != today.month:
        continue
      if not self.env['hr.leave.allocation'].search(
          [('employee_id', '=', employee.id),
           ('holiday_status_id', '=', leave_type.id),
           ('date_from', '>=', today + relativedelta(day=1, month=1)),
           ('date_from', '<=', today + relativedelta(day=31, month=12))]):
        allocation = self.env['hr.leave.allocation'].create({
          'name': 'Sinh nhật %s' % employee.name,
          'multi_employee': False,
          'holiday_status_id': leave_type.id,
          'holiday_type': 'employee',
          'employee_id': employee.id,
          'employee_ids': [(6, 0, employee.ids)],
          'date_from': today + relativedelta(day=1),
          'date_to': today + relativedelta(day=1, months=1, days=-1),
          'number_of_days': 1,
        })
        allocation.action_confirm()
        allocation.action_validate()

  def action_change_date_end(self, local_time):
    resource_details = self.env['en.resource.detail'].search([
      ('employee_id', '=', self.id), ('date_start', '<', local_time),
      ('date_end', '>=', local_time)
    ])
    for resource in resource_details:
      message = f'''
                Nhân sự {resource.employee_id.name} Ngày kết thúc: {resource.date_end.strftime('%d/%m/%Y')} → {local_time.strftime('%d/%m/%Y')}
            '''
      resource.sudo().write({
        'date_end': local_time - relativedelta(days=1)
      })
      resource.order_id.message_post(body=message)

  @api.constrains('en_date_start', 'departure_date')
  def _constrains_departure_date_en_date_start(self):
    if any((not rec.en_date_start and rec.departure_date) or (
        rec.en_date_start and rec.departure_date and rec.en_date_start > rec.departure_date)
           for rec in self):
      raise exceptions.ValidationError(
        'Ngày dừng hoạt động nhân viên không thể nhỏ hơn ngày bắt đầu làm việc của nhân viên')

  @api.constrains('en_date_start', 'en_day_layoff_from')
  def _constrains_en_day_layoff_from_en_date_start(self):
    if any((not rec.en_date_start and rec.en_day_layoff_from) or (
        rec.en_date_start and rec.en_day_layoff_from and rec.en_date_start > rec.en_day_layoff_from)
           for rec in self):
      raise exceptions.ValidationError(
        'Ngày tạm dừng hoạt động của nhân viên không thể nhỏ hơn ngày bắt đầu làm việc của nhân viên.')

  def _sync_user(self, user, employee_has_image=False):
    vals = dict(
        user_id=user.id,
    )
    if not employee_has_image:
      vals['image_1920'] = user.image_1920
    if user.tz:
      vals['tz'] = user.tz
    return vals

  def default_get(self, fields_list):
    res = super(HrEmployee, self).default_get(fields_list)
    if 'role_ids' in fields_list:
      res['role_ids'] = self.env['entrust.role'].search(
          [('name', '=', 'Thành viên dự án')]).ids
    if self.env.context.get('hidden'):
      res['en_type_id'] = self.env['en.type'].search([('is_hidden', '=', True)],
                                                     limit=1).id
    return res

  def button_resource_account_report_wizard_act(self):
    return self.open_form_or_tree_view(
      'account_reports.resource_account_report_wizard_act', False, False,
      {'default_employee_id': self.id}, 'Thông tin nguồn lực', 'new')

  def unlink(self):
    expt = []
    for rec in self:
      resources = self.env['en.resource.detail'].search(
          [('employee_id', '=', rec.id)])
      if not resources: continue
      expt += [
        f'Nhân viên {rec.display_name} đang ở trong kế hoạch nguồn lực của dự án {", ".join(list(set(resources.mapped("order_id.project_id.display_name"))))}']
    if expt: raise exceptions.UserError('\n'.join(expt))
    return super().unlink()

  def read(self, fields=None, load='_classic_read'):
    if not self._context.get('recompute_en_status'):
      self.recompute_en_status()
    return super().read(fields=fields, load=load)

  def recompute_en_status(self):
    self = self.sudo()
    for rec in self:
      if rec.en_status != 'semi-inactive': continue
      if rec.en_day_layoff_to and rec.en_day_layoff_to < fields.Date.today() and rec.en_status != 'active':
        rec.with_context(recompute_en_status=True).write(
            {'en_status': 'active'})

  def toggle_active(self):
    res = super().toggle_active()
    record_active = self.filtered(lambda record: record.active)
    if record_active:
      record_active.write({'en_status': 'active'})
    return res

  def en_button_layoff(self):
    record = self.env['hr.employee.layoff.wizard'].create(
        {'employee_id': self.id})
    return self.open_form_or_tree_view(
      'ngsd_base.hr_employee_layoff_wizard_act', False, record, {}, 'Nghỉ việc',
      'new')

  en_text_off = fields.Text(string='Lý do nghỉ việc', readonly=True, copy=False,
                            groups="hr.group_hr_user")
  en_day_layoff_from = fields.Date(string='Ngày bắt đầu tạm dừng làm việc',
                                   readonly=False, copy=False,
                                   groups="hr.group_hr_user")
  en_day_layoff_to = fields.Date(string='Ngày kết thúc tạm dừng làm việc',
                                 readonly=False, copy=False,
                                 groups="hr.group_hr_user")
  en_text_layoff = fields.Text(string='Lý do nghỉ dài hạn', readonly=False,
                               copy=False, groups="hr.group_hr_user")

  _sql_constraints = [
    ('barcode_uniq', 'unique (id)',
     "The Badge ID must be unique, this one is already assigned to another employee."),
  ]

  @api.constrains('barcode', 'work_email', 'en_type_id')
  def _ngsd_constrains_duplicate(self):
    for rec in self:
      if rec.en_internal_ok and self.search_count(
          [('barcode', '=', rec.barcode)]) > 1:
        raise exceptions.ValidationError(
          'Mã nhân sự/ Email bị trùng, vui lòng kiểm tra lại!')
      if rec.en_internal_ok and self.search_count(
          [('work_email', '=', rec.work_email)]) > 1:
        raise exceptions.ValidationError(
          'Mã nhân sự/ Email bị trùng, vui lòng kiểm tra lại!')
    # if any((rec.en_internal_ok and self.search_count([('barcode', '=', rec.barcode)]) > 1) or (self.search_count([('work_email', '=', rec.work_email)]) > 1) for rec in self):
    #     raise exceptions.ValidationError('Mã nhân sự/ Email bị trùng, vui lòng kiểm tra lại!')

  work_email = fields.Char(required=False)
  department_id = fields.Many2one(required=False)
  job_id = fields.Many2one(required=False)
  barcode = fields.Char(required=False)
  en_status = fields.Selection(string='Trạng thái', groups="hr.group_hr_user",
                               selection=[('active', 'Hoạt động'),
                                          ('inactive', 'Nghỉ việc'),
                                          ('semi-inactive', 'Nghỉ dài hạn')],
                               default='active', copy=False, required=True)
  en_status_hr = fields.Selection(string='Trạng thái',
                                  groups="hr.group_hr_user",
                                  selection=[('active', 'Hoạt động'),
                                             ('inactive', 'Nghỉ việc'),
                                             ('semi-inactive',
                                              'Nghỉ không lương'),
                                             ('maternity-leave',
                                              'Nghỉ thai sản')],
                                  default='active', store=True, copy=False,
                                  compute='_get_en_status_hr',
                                  inverse='_inverse_en_status_hr')

  has_child_start = fields.Date(string="Ngày hưởng chế độ có con nhỏ")
  has_child_end = fields.Date(string="Ngày kết thúc hưởng chế độ có con nhỏ")

  @api.depends('en_status')
  def _get_en_status_hr(self):
    for rec in self:
      if rec.en_status_hr == 'maternity-leave' and rec.en_status == 'semi-inactive':
        rec.en_status_hr = 'maternity-leave'
        continue
      rec.en_status_hr = rec.en_status

  def _inverse_en_status_hr(self):
    for rec in self:
      en_status = rec.en_status_hr
      if rec.en_status_hr == 'maternity-leave':
        en_status = 'semi-inactive'
      if rec.en_status != en_status:
        rec.en_status = en_status

  en_type_id = fields.Many2one(required=False, string='Loại',
                               comodel_name='en.type',
                               groups="hr.group_hr_user")
  # Lấy giá trị is_intern từ en_type_id
  is_intern = fields.Boolean(string='Thực tập sinh',
                             related='en_type_id.is_intern', readonly=True,
                             store=True)
  en_internal_ok = fields.Boolean(related='en_type_id.internal_ok',
                                  groups="hr.group_hr_user")
  is_hidden = fields.Boolean(related='en_type_id.is_hidden',
                             groups="hr.group_hr_user")
  en_area_id = fields.Many2one(required=False, string='Khu vực',
                               comodel_name='en.name.area',
                               groups="hr.group_hr_user")
  en_date_start = fields.Date(required=False, string='Ngày bắt đầu',
                              default=lambda self: fields.Date.today(),
                              groups="hr.group_hr_user")
  en_block_id = fields.Many2one(required=False, string='Khối',
                                comodel_name='en.name.block',
                                groups="hr.group_hr_user",
                                domain="['|', ('area_id', '=?', en_area_id),('en_area_ids', '=', en_area_id)]")
  job_title = fields.Char(readonly=True)
  en_department_id = fields.Many2one(string='Phòng',
                                     comodel_name='en.department',
                                     groups="hr.group_hr_user",
                                     domain="[('department_id', '=', department_id)]")
  en_level_id = fields.Many2one(required=False, string='Cấp bậc',
                                comodel_name='en.name.level',
                                groups="hr.group_hr_user")
  en_technique = fields.Char(required=False, string='Kỹ năng',
                             groups="hr.group_hr_user")
  en_date_from = fields.Date(readonly=True, copy=False, string='Ngày bắt đầu',
                             groups="hr.group_hr_user")
  en_date_to = fields.Date(readonly=True, copy=False, string='Ngày kết thúc',
                           groups="hr.group_hr_user")

  target_quarter = fields.Float(string="Chỉ tiêu quý", default=0,
                                groups="hr.group_hr_user")
  target_year = fields.Float(string="Chỉ tiêu năm", default=0,
                             groups="hr.group_hr_user")

  start_date_quarter = fields.Date(string="Áp dụng từ ngày",
                                   groups="hr.group_hr_user")
  end_date_quarter = fields.Date(string="Áp dụng đến ngày",
                                 groups="hr.group_hr_user")

  start_date_year = fields.Date(string="Áp dụng từ ngày",
                                groups="hr.group_hr_user")
  end_date_year = fields.Date(string="Áp dụng đến ngày",
                              groups="hr.group_hr_user")

  @api.onchange('department_id')
  def _onchange_en_department_id(self):
    for rec in self:
      rec.en_department_id = False

  @api.onchange('en_area_id')
  def _onchange_en_area_id(self):
    for rec in self:
      rec.en_block_id = False

  @api.onchange('en_block_id')
  def _onchange_en_block_id(self):
    for rec in self:
      rec.department_id = False

  def get_revenue_quarter(self):
    user_ids = self.env.user | self.subordinate_ids.user_id
    domain = [('user_id', 'in', user_ids.ids),
              ('date_deadline', '>=', self.start_date_quarter),
              ('date_deadline', '<=', self.end_date_quarter)]
    total_revenue = sum(
      self.env['crm.lead'].search(domain).mapped('total_revenue'))
    return total_revenue

  def get_revenue_year(self):
    user_ids = self.env.user | self.subordinate_ids.user_id
    domain = [('user_id', 'in', user_ids.ids),
              ('date_deadline', '>=', self.start_date_year),
              ('date_deadline', '<=', self.end_date_year)]
    total_revenue = sum(
      self.env['crm.lead'].search(domain).mapped('total_revenue'))
    return total_revenue

  def noti_not_target_quarter(self):
    dash_board = self.env.ref('kpi_dashboard.demo_dashboard')
    base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
    report_action = 'kpi_dashboard.ngsd_crm_dashboard'
    action = self.env.ref(report_action)
    link = f'{base_url}/web#id={dash_board.id}&action={action.id}&model=kpi.dashboard&view_type=dashboard'
    emps = self.search([('target_quarter', '>', 0)])
    for emp in emps:
      total_revenue = emp.get_revenue_quarter()
      if total_revenue < emp.target_quarter:
        mes = 'Chưa đạt chỉ tiêu quý'
        emp.send_notify(mes, emp.user_id, link=link,
                        model_description="Dashboard")
    return {
      'type': 'ir.actions.client',
      'tag': 'display_notification',
      'params': {
        'message': 'Gửi thông báo thành công!',
        'title': 'Thành công',
        'type': 'success',
        'sticky': False,
      }
    }

  def noti_not_target_year(self):
    dash_board = self.env.ref('kpi_dashboard.demo_dashboard')
    base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
    report_action = 'kpi_dashboard.ngsd_crm_dashboard'
    action = self.env.ref(report_action)
    link = f'{base_url}/web#id={dash_board.id}&action={action.id}&model=kpi.dashboard&view_type=dashboard'
    emps = self.search([('target_year', '>', 0)])
    for emp in emps:
      total_revenue = emp.get_revenue_year()
      if total_revenue < emp.target_year:
        mes = 'Chưa đạt chỉ tiêu năm'
        emp.send_notify(mes, emp.user_id, link=link,
                        model_description="Dashboard")
    return {
      'type': 'ir.actions.client',
      'tag': 'display_notification',
      'params': {
        'message': 'Gửi thông báo thành công!',
        'title': 'Thành công',
        'type': 'success',
        'sticky': False,
      }
    }

  def update_total_target_quarter(self, start, end):
    if not start:
      start = self.child_ids[:1].start_date_quarter
    if not end:
      end = self.child_ids[:1].end_date_quarter
    self.write({
      'target_quarter': sum(self.child_ids.mapped('target_quarter')),
      'start_date_quarter': start,
      'end_date_quarter': end,
    })

  def update_total_target_year(self, start, end):
    if not start:
      start = self.child_ids[:1].start_date_year
    if not end:
      end = self.child_ids[:1].end_date_year
    self.with_context(no_compute_parent=True).write({
      'target_year': sum(self.child_ids.mapped('target_year')),
      'start_date_year': start,
      'end_date_year': end,
    })

  @api.model_create_multi
  def create(self, vals_list):
    # Handle both single record and batch creation
    if not isinstance(vals_list, list):
      vals_list = [vals_list]

    lock_create_timesheet = self.env['lock.license'].get_lasted_date_lock(
      'create')
    lock_approve_timesheet = self.env['lock.license'].get_lasted_date_lock(
      'approve')
    fields = ['target_quarter', 'target_year', 'start_date_quarter',
              'end_date_quarter', 'start_date_year', 'end_date_year']

    for vals in vals_list:
      if lock_create_timesheet:
        vals['lock_create_timesheet'] = lock_create_timesheet
      if lock_approve_timesheet:
        vals['lock_approve_timesheet'] = lock_approve_timesheet

    res = super().create(vals_list)

    for record, vals in zip(res, vals_list):
      if not record.user_id and record.work_email:
        record.user_id = self.env['res.users'].sudo().create({
          'name': record.name,
          'email': record.work_email,
          'login': record.work_email,
          'image_1920': record.image_1920,
          'role_ids': [(6, 0, record.role_ids.ids)],
          'tz': record.tz,
        })

      match_fields = list(set(fields) & set(vals.keys()))
      if match_fields and record.parent_id:
        record.parent_id.update_total_target_quarter(record.start_date_quarter,
                                                     record.end_date_quarter)
        record.parent_id.update_total_target_year(record.start_date_year,
                                                  record.end_date_year)

      self.env['en.technical.model'].manual_create_technical_compute(record,
                                                                     datetime.now() + relativedelta(
                                                                       years=-1,
                                                                       month=1,
                                                                       day=1,
                                                                       hour=0,
                                                                       minute=0,
                                                                       second=0),
                                                                     datetime.now() + relativedelta(
                                                                       years=2,
                                                                       month=12,
                                                                       day=31,
                                                                       hour=23,
                                                                       minute=59,
                                                                       second=59))

    return res

  def write(self, vals):
    if 'lock_create_timesheet' in vals or 'lock_create_timesheet_exp' in vals:
      raise UserError('Không được phép chỉnh sửa ngày khóa sổ khai Timesheet')
    if 'lock_approve_timesheet' in vals or 'lock_approve_timesheet_exp' in vals:
      raise UserError('Không được phép chỉnh sửa ngày khóa sổ duyệt Timesheet')
    if 'state_hr_employee' in vals:
      for rec in self:
        if rec.en_status == 'semi-inactive' and rec.state_hr_employee in [
          'maternity', 'semi-inactive']:
          raise UserError(
            "Bạn không thể đổi Tình trạng khi đang trong thời gian Nghỉ không lương/Nghỉ thai sản")
    if len(self) == 1:
      if vals.get('en_status_hr') in ['semi-inactive', 'maternity-leave']:
        vals['state_hr_employee'] = vals.get('en_status_hr').replace('-leave',
                                                                     '')
        if not self.old_state_hr_employee:
          vals['old_state_hr_employee'] = self.state_hr_employee
      if vals.get('en_status') == 'active' and self.old_state_hr_employee:
        vals['state_hr_employee'] = self.old_state_hr_employee
        vals['old_state_hr_employee'] = False
    res = super().write(vals)
    if 'role_ids' in vals:
      self.user_id.sudo().write({'role_ids': vals['role_ids']})
    if 'departure_date' in vals:
      for rec in self:
        if rec.departure_date and rec.departure_date <= fields.Date.Date.context_today(
            self):
          rec.action_departure()

    if self._context.get('no_compute_parent'):
      return res
    lst_fields = ['target_quarter', 'target_year', 'start_date_quarter',
                  'end_date_quarter', 'start_date_year', 'end_date_year']
    match_fields = list(set(lst_fields) & set(vals.keys()))
    for rec in self:
      if match_fields and rec.parent_id:
        rec.parent_id.update_total_target_quarter(rec.start_date_quarter,
                                                  rec.end_date_quarter)
        rec.parent_id.update_total_target_year(rec.start_date_year,
                                               rec.end_date_year)
    if 'resource_calendar_id' in vals:
      for rec in self:
        miss_match = self.env['resource.calendar.leaves'].sudo().search(
            [('resource_id.user_id', '=', rec.user_id.id),
             ('calendar_id', '!=', rec.resource_calendar_id.id)])
        if miss_match:
          miss_match.sudo().write({'calendar_id': rec.resource_calendar_id.id})
    return res

  # Add context pass constrains timesheet
  def _delete_future_public_holidays_timesheets(self):
    self = self.with_context(no_constrains=True)
    return super(HrEmployee, self)._delete_future_public_holidays_timesheets()

  # Add context pass constrains timesheet
  def _create_future_public_holidays_timesheets(self, employees):
    self = self.with_context(no_constrains=True)
    return super(HrEmployee, self)._create_future_public_holidays_timesheets(
      employees)

  @api.constrains('en_type_id', 'barcode', 'work_email', 'en_area_id',
                  'en_block_id', 'department_id', 'job_id', 'en_level_id',
                  'en_date_start')
  def check_required_field(self):
    fields_check = ['work_email', 'department_id', 'job_id', 'en_level_id',
                    'en_date_start']
    fields_check_not_os = ['en_area_id', 'en_block_id']
    for rec in self:
      if rec.is_hidden or rec.en_type_id.is_os:
        continue
      if any(not rec[f] for f in fields_check):
        raise UserError('Thiếu thông tin bắt buộc')
      if not rec.en_type_id.is_os and any(
          not rec[f] for f in fields_check_not_os):
        raise UserError('Thiếu thông tin bắt buộc')

  check_timesheet_before_checkout = fields.Boolean('Bắt buộc khai timesheet',
                                                   groups='hr.group_hr_user',
                                                   default=True)

  def get_hour_working_by_day(self, day):
    # thời gian không làm việc
    tech_data = self.env['en.technical.model'].convert_daterange_to_data(self,
                                                                         day,
                                                                         day)
    if tech_data[day].get('tech_type') in ['off', 'not_work', 'layoff',
                                           'holiday']:
      return -1
    calendar = self.resource_calendar_id or self.env.company.resource_calendar_id
    # # thời gian nghỉ phép
    # leave_hour = 8 - tech_data[day].get('number')
    # Khai ts
    ts_hour = sum(self.env['account.analytic.line'].search(
        [('employee_id', '=', self.id), ('date', '=', day),
         ('en_state', 'in', ['approved'])]).mapped('unit_amount'))
    # Khai nghỉ phép
    hr_leave = self.env['hr.leave'].search(
        [('employee_id', '=', self.id), ('request_date_from', '<=', day),
         ('request_date_to', '>=', day), ('state', 'in', ['validate']),
         ('holiday_status_id.code', '!=', 'W')])
    leave_hour = sum([min(
      max(l.number_of_hours_display, l.number_of_days * calendar.hours_per_day),
      8) for l in hr_leave])
    return ts_hour + leave_hour

  role_ids = fields.Many2many('entrust.role', string='Vai trò phân quyền',
                              required=0)

  @api.model
  def _name_search(self, name, args=None, operator='ilike', limit=100,
      name_get_uid=None):
    args = args or []
    employee_ids = []
    if self._context.get('view_all_hr_employee') and self.env.user.has_group(
        'ngsd_base.group_hcns'):
      self = self.sudo()
    if self._context.get('import_file'):
      self = self.with_context(active_test=False)
    if operator not in expression.NEGATIVE_TERM_OPERATORS:
      if operator == 'ilike' and not (name or '').strip():
        domain = []
      else:
        domain = ['|', ('work_email', '=', name), ('barcode', '=', name)]
      employee_ids = self._search(expression.AND([domain, args]), limit=limit,
                                  access_rights_uid=name_get_uid)
    if not employee_ids:
      employee_ids = self._search(
        expression.AND([[('name', operator, name)], args]), limit=limit,
        access_rights_uid=name_get_uid)
    return employee_ids

  timesheet_general_ids = fields.One2many('timesheet.general', 'employee_id',
                                          'Bảng tổng hợp chấm công')

  def button_timesheet_general(self):
    self.env['timesheet.general'].init_data(self.id)
    action = {
      'type': 'ir.actions.act_window',
      'name': 'Bảng tổng hợp chấm công',
      'res_model': 'timesheet.general',
      'views': [[False, 'calendar'], [False, 'list']],
      'domain': [('employee_id', '=', self.id)],
      'target': 'self',
      'context': {'create': 0, 'edit': 0, 'delete': 0}
    }
    return action

  def button_user_reset_password(self):
    if not self.user_id:
      raise UserError('Người dùng chưa được tạo')
    return self.user_id.sudo().action_reset_password()

  def button_user_reset_login_failed_number(self):
    if not self.user_id:
      raise UserError('Người dùng chưa được tạo')
    return self.user_id.sudo().reset_login_failed_number()

  def button_user_reset_password(self):
    if not self.user_id:
      raise UserError('Người dùng chưa được tạo')
    return self.user_id.sudo().action_reset_password()

  def button_user_reset_login_failed_number(self):
    if not self.user_id:
      raise UserError('Người dùng chưa được tạo')
    return self.user_id.sudo().reset_login_failed_number()


class EntrustRole(models.Model):
  _inherit = 'entrust.role'

  def copy(self, default=None):
    default = default or {}
    if not default.get('name'):
      default['name'] = "%s (sao chép)" % self.name
    res = super(EntrustRole, self).copy(default)
    return res


class SalaryGrade(models.Model):
  _name = 'salary.grade'
  _description = 'Bậc lương'

  name = fields.Char(string='Bậc lương', required=True)


class PayGrade(models.Model):
  _name = 'pay.grade'
  _description = 'Mức lương'

  name = fields.Char(string='Pay Grade', required=True)


class DependPerson(models.Model):
  _name = 'depend.persion'
  _description = 'Người phụ thuộc'

  relationship = fields.Selection(
      [('parent', 'Cha Mẹ'), ('child', 'Con'), ('couple', 'Vợ/Chồng'),
       ('other', 'Khác')], string='Quan hệ', required=True)
  full_name = fields.Char(string='Họ và tên')
  date_of_birth = fields.Date(string='Ngày sinh')
  people_id = fields.Char(string='CMND/Căn cước')
  reduce = fields.Float(string='Giảm trừ')
  reduce_from = fields.Date(string='Giảm trừ từ')
  reduce_to = fields.Date(string='Giảm trừ đến')
  note = fields.Char(string='Ghi chú')
  hr_employee_id = fields.Many2one(comodel_name='hr.employee',
                                   string='Nhân viên', required=True,
                                   ondelete='cascade')


class HrResumeLineInheit(models.Model):
  _inherit = 'hr.resume.line'

  name_project = fields.Char(string='Tên dự án')
  domain_project = fields.Char(string='Domain dự án')
  service_provided = fields.Char(string='Dịch vụ cung cấp')
  position_responsibility = fields.Char(string='Vị trí đảm nhiệm')
  hr_resume_type = fields.Selection(related='line_type_id.hr_resume_type',
                                    string='Loại sơ yếu lý lịch')
  specialized = fields.Char(string='Chuyên ngành')
  date_start = fields.Date(required=False)
  graduation_year = fields.Integer(string='Năm tốt nghiệp')


class HrResumeLineType(models.Model):
  _inherit = 'hr.resume.line.type'

  hr_resume_type = fields.Selection(
      [('exp', 'Experience'), ('edu', 'Education')], required=True,
      string='Loại sơ yếu lý lịch')


class EmployeeSkill(models.Model):
  _inherit = 'hr.employee.skill'

  skill_id = fields.Many2one(required=False)
  skill_level_id = fields.Many2one(required=False)
  skill_type_id = fields.Many2one(required=False)


class ResPartnerBank(models.Model):
  _inherit = 'res.partner.bank'

  hr_employee_id = fields.Many2one(comodel_name='hr.employee',
                                   string='Nhân viên')


class TimesheetGeneral(models.Model):
  _name = 'timesheet.general'
  _description = 'Bảng tổng hợp chấm công'

  employee_id = fields.Many2one('hr.employee', 'Nhân viên')
  date = fields.Date('Ngày')
  total_time = fields.Float('Tổng thời gian')
  type = fields.Selection(selection=[
    ('ts_new', 'TS Mới'),
    ('ts_pending', 'TS Chờ duyệt'),
    ('ts_approved', 'TS Đã duyệt'),
    ('ot_pending', 'OT Chờ duyệt'),
    ('ot_approved', 'OT Đã duyệt'),
    ('plan_ot_pending', 'Plan OT Chờ duyệt'),
    ('leave_approved', 'Nghỉ phép đã duyệt'),
    ('leave_draft', 'Nghỉ phép mới'),
    ('leave_confirm', 'Nghỉ phép chờ duyệt'),
    ('leave_holiday', 'Nghỉ lễ'),
  ], required=True, string='Loại')
  color = fields.Integer(compute='_compute_color')
  text_content = fields.Text('Chi tiết')

  @api.depends('type')
  def _compute_color(self):
    for rec in self:
      if rec.type == 'ts_new':
        rec.color = 4
      elif rec.type == 'ts_pending':
        rec.color = 2
      elif rec.type == 'ts_approved':
        rec.color = 10
      elif rec.type == 'ot_approved':
        rec.color = 1
      elif rec.type == 'leave_holiday':
        rec.color = 9
      elif rec.type in ['ot_pending', 'plan_ot_pending']:
        rec.color = 3
      elif rec.type == 'leave_confirm':
        rec.color = 2
      elif rec.type == 'leave_draft':
        rec.color = 4
      elif rec.type == 'leave_approved':
        rec.color = 10
      else:
        rec.color = 8

  def name_get(self):
    names = []
    for record in self:
      name = f"{dict(self._fields['type'].selection).get(record.type)}: {record.total_time} giờ"
      names.append((record.id, name))
    return names

  def init_data(self, employee):
    self.search([('employee_id', '=', employee)]).unlink()
    user_id = self.env['hr.employee'].browse(employee).user_id.id
    values = []
    ts_new = self.env['account.analytic.line'].read_group(
        [('employee_id', '=', employee), ('holiday_id', '=', False),
         ('en_state', '=', 'new'), '|', ('project_id.active', '=', True),
         ('en_nonproject_task_id', '!=', False), ], ['unit_amount'],
        ['date:day'])
    for ts_n in ts_new:
      text_context_new = """"""
      ts_new_p = self.env['account.analytic.line'].read_group(
          [('employee_id', '=', employee), ('en_state', '=', 'new'),
           ('project_id.active', '=', True),
           ('date', '=', ts_n['__range']['date']['from'])], ['unit_amount'],
          ['project_id'])
      ts_new_np = self.env['account.analytic.line'].read_group(
          [('employee_id', '=', employee), ('en_state', '=', 'new'),
           ('en_nonproject_task_id', '!=', False),
           ('date', '=', ts_n['__range']['date']['from'])], ['unit_amount'],
          ['en_nonproject_task_id'])
      for ts_new in ts_new_p:
        if ts_new['unit_amount'] > 0:
          text_context_new += f"""  {self.env['project.project'].browse(ts_new['project_id'][0]).en_code} : {round(ts_new['unit_amount'], 2)} giờ \n""" if \
          ts_new[
            'project_id'] else f"""  : {round(ts_new['unit_amount'], 2)} giờ \n"""
      for ts_new_n in ts_new_np:
        if ts_new_n['unit_amount'] > 0:
          text_context_new += f"""  {self.env['en.nonproject.task'].browse(ts_new_n['en_nonproject_task_id'][0]).en_department_id.name} : {round(ts_new_n['unit_amount'], 2)} giờ \n""" if \
          ts_new_n[
            'en_nonproject_task_id'] else f"""  : {round(ts_new_n['unit_amount'], 2)} giờ \n"""
      values.append({
        'date': ts_n['__range']['date']['from'],
        'employee_id': employee,
        'total_time': round(ts_n['unit_amount'], 2),
        'type': 'ts_new',
        'text_content': text_context_new
      })
    ts_pending = self.env['account.analytic.line'].read_group(
        [('employee_id', '=', employee), ('en_state', '=', 'sent'), '|',
         ('project_id.active', '=', True),
         ('en_nonproject_task_id', '!=', False), ], ['unit_amount'],
        ['date:day'])
    for ts_p in ts_pending:
      text_context_pending = """"""
      ts_pending_p = self.env['account.analytic.line'].read_group(
          [('employee_id', '=', employee), ('en_state', '=', 'sent'),
           ('project_id.active', '=', True),
           ('date', '=', ts_p['__range']['date']['from'])], ['unit_amount'],
          ['project_id'])
      ts_pending_np = self.env['account.analytic.line'].read_group(
          [('employee_id', '=', employee), ('en_state', '=', 'sent'),
           ('en_nonproject_task_id', '!=', False),
           ('date', '=', ts_p['__range']['date']['from'])], ['unit_amount'],
          ['en_nonproject_task_id'])
      for ts_pending in ts_pending_p:
        if ts_pending['unit_amount'] > 0:
          text_context_pending += f"""  {self.env['project.project'].browse(ts_pending['project_id'][0]).en_code} : {round(ts_pending['unit_amount'], 2)} giờ \n""" if \
          ts_pending[
            'project_id'] else f"""  : {round(ts_pending['unit_amount'], 2)} giờ \n"""
      for ts_pending_n in ts_pending_np:
        if ts_pending_n['unit_amount'] > 0:
          text_context_pending += f"""  {self.env['en.nonproject.task'].browse(ts_pending_n['en_nonproject_task_id'][0]).en_department_id.name} : {round(ts_pending_n['unit_amount'], 2)} giờ \n""" if \
          ts_pending_n[
            'en_nonproject_task_id'] else f"""  : {round(ts_pending_n['unit_amount'], 2)} giờ \n"""
      values.append({
        'date': ts_p['__range']['date']['from'],
        'employee_id': employee,
        'total_time': round(ts_p['unit_amount'], 2),
        'type': 'ts_pending',
        'text_content': text_context_pending
      })
    ts_approved = self.env['account.analytic.line'].read_group(
        [('employee_id', '=', employee), ('en_state', '=', 'approved'), '|',
         ('project_id.active', '=', True),
         ('en_nonproject_task_id', '!=', False), ], ['unit_amount', 'date:max'],
        ['date:day'])
    for ts_a in ts_approved:
      text_context_approved = """"""
      ts_approved_p = self.env['account.analytic.line'].read_group(
          [('employee_id', '=', employee), ('en_state', '=', 'approved'),
           ('project_id.active', '=', True),
           ('date', '=', ts_a['__range']['date']['from'])], ['unit_amount'],
          ['project_id'])
      ts_approved_np = self.env['account.analytic.line'].read_group(
          [('employee_id', '=', employee), ('en_state', '=', 'approved'),
           ('en_nonproject_task_id', '!=', False),
           ('date', '=', ts_a['__range']['date']['from'])], ['unit_amount'],
          ['en_nonproject_task_id'])
      for ts_a_p in ts_approved_p:
        if ts_a_p['unit_amount'] > 0:
          text_context_approved += f"""  {self.env['project.project'].browse(ts_a_p['project_id'][0]).en_code} : {round(ts_a_p['unit_amount'], 2)} giờ \n""" if \
            ts_a_p[
              'project_id'] else f"""  : {round(ts_a_p['unit_amount'], 2)} giờ \n"""
      for ts_a_n in ts_approved_np:
        if ts_a_n['unit_amount'] > 0:
          text_context_approved += f"""  {self.env['en.nonproject.task'].browse(ts_a_n['en_nonproject_task_id'][0]).en_department_id.name} : {round(ts_a_n['unit_amount'], 2)} giờ \n""" if \
            ts_a_n[
              'en_nonproject_task_id'] else f"""  : {round(ts_a_n['unit_amount'], 2)} giờ \n"""
      values.append({
        'date': ts_a['__range']['date']['from'],
        'employee_id': employee,
        'total_time': round(ts_a['unit_amount'], 2),
        'type': 'ts_approved',
        'text_content': text_context_approved
      })
    ot_pending = self.env['account.analytic.line'].read_group(
        [('employee_id', '=', employee), ('ot_state', '=', 'requested'), '|',
         ('project_id.active', '=', True),
         ('en_nonproject_task_id', '!=', False), ], ['ot_time'], ['date:day'])
    for ot_p in ot_pending:
      text_context_pending_ot = """"""
      ot_pending_p = self.env['account.analytic.line'].read_group(
          [('employee_id', '=', employee), ('ot_state', '=', 'requested'),
           ('project_id.active', '=', True),
           ('date', '=', ot_p['__range']['date']['from'])], ['ot_time'],
          ['project_id'])
      ot_pending_np = self.env['account.analytic.line'].read_group(
          [('employee_id', '=', employee), ('ot_state', '=', 'requested'),
           ('en_nonproject_task_id', '!=', False),
           ('date', '=', ot_p['__range']['date']['from'])], ['ot_time'],
          ['en_nonproject_task_id'])
      for ot_pending in ot_pending_p:
        if ot_pending['ot_time'] > 0:
          text_context_pending_ot += f"""  {self.env['project.project'].browse(ot_pending['project_id'][0]).en_code} : {round(ot_pending['ot_time'], 2)} giờ \n""" if \
          ot_pending[
            'project_id'] else f"""  : {round(ot_pending['ot_time'], 2)} giờ \n"""
      for ot_pending_n in ot_pending_np:
        if ot_pending_n['ot_time'] > 0:
          text_context_pending_ot += f"""  {self.env['en.nonproject.task'].browse(ot_pending_n['en_nonproject_task_id'][0]).en_department_id.name} : {round(ot_pending_n['ot_time'], 2)} giờ \n""" if \
          ot_pending_n[
            'en_nonproject_task_id'] else f"""  : {round(ot_pending_n['ot_time'], 2)} giờ \n"""
      values.append({
        'date': ot_p['__range']['date']['from'],
        'employee_id': employee,
        'total_time': round(ot_p['ot_time'], 2),
        'type': 'ot_pending',
        'text_content': text_context_pending_ot
      })
    ot_approved = self.env['account.analytic.line'].read_group(
        [('employee_id', '=', employee), ('ot_state', '=', 'approved'), '|',
         ('project_id.active', '=', True),
         ('en_nonproject_task_id', '!=', False), ], ['ot_time'], ['date:day'])
    for ot in ot_approved:
      text_context_ot_approved = """"""
      ot_approved_p = self.env['account.analytic.line'].read_group(
          [('employee_id', '=', employee), ('ot_state', '=', 'approved'),
           ('project_id.active', '=', True),
           ('date', '=', ot['__range']['date']['from'])], ['ot_time'],
          ['project_id'])
      ot_approved_np = self.env['account.analytic.line'].read_group(
          [('employee_id', '=', employee), ('ot_state', '=', 'approved'),
           ('en_nonproject_task_id', '!=', False),
           ('date', '=', ot['__range']['date']['from'])], ['ot_time'],
          ['en_nonproject_task_id'])
      for ot_a_p in ot_approved_p:
        if ot_a_p['ot_time'] > 0:
          text_context_ot_approved += f"""  {self.env['project.project'].browse(ot_a_p['project_id'][0]).en_code} : {round(ot_a_p['ot_time'], 2)} giờ \n""" if \
          ot_a_p[
            'project_id'] else f"""  : {round(ot_a_p['ot_time'], 2)} giờ \n"""
      for ot_a_n in ot_approved_np:
        if ot_a_n['ot_time'] > 0:
          text_context_ot_approved += f"""  {self.env['en.nonproject.task'].browse(ot_a_n['en_nonproject_task_id'][0]).en_department_id.name} : {round(ot_a_n['ot_time'], 2)} giờ \n""" if \
          ot_a_n[
            'en_nonproject_task_id'] else f"""  : {round(ot_a_n['ot_time'], 2)} giờ \n"""
      values.append({
        'date': ot['__range']['date']['from'],
        'employee_id': employee,
        'total_time': round(ot['ot_time'], 2),
        'type': 'ot_approved',
        'text_content': text_context_ot_approved
      })
    plan_ot_pending = self.env['en.overtime.plan'].read_group(
        [('create_uid', '=', user_id), ('state', '=', 'to_approve')],
        ['en_hours'], ['en_date:day'])
    for plan_ot in plan_ot_pending:
      text_context_plan = """"""
      plan_ot_pending_p = self.env['en.overtime.plan'].read_group(
          [('create_uid', '=', user_id), ('state', '=', 'to_approve'),
           ('en_work_inproject', '=', True),
           ('en_date', '=', plan_ot['__range']['en_date']['from'])],
          ['en_hours'], ['en_project_id'])
      plan_ot_pending_np = self.env['en.overtime.plan'].read_group(
          [('create_uid', '=', user_id), ('state', '=', 'to_approve'),
           ('en_work_inproject', '=', False),
           ('en_date', '=', plan_ot['__range']['en_date']['from'])],
          ['en_hours'], ['en_work_nonproject_id'])
      for plan_ot_p in plan_ot_pending_p:
        if plan_ot_p['en_hours'] > 0:
          text_context_plan += f"""  {self.env['project.project'].browse(plan_ot_p['en_project_id'][0]).en_code} : {round(plan_ot_p['en_hours'], 2)} giờ \n""" if \
          plan_ot_p[
            'en_project_id'] else f"""  : {round(plan_ot_p['en_hours'], 2)} giờ \n"""
      for plan_ot_np in plan_ot_pending_np:
        if plan_ot_np['en_hours'] > 0:
          text_context_plan += f"""  {self.env['en.nonproject.task'].browse(plan_ot_np['en_work_nonproject_id'][0]).en_department_id.name} : {round(plan_ot_np['en_hours'], 2)} giờ \n""" if \
          plan_ot_np[
            'en_work_nonproject_id'] else f"""  : {round(plan_ot_np['en_hours'], 2)} giờ \n"""
      values.append({
        'date': plan_ot['__range']['en_date']['from'],
        'employee_id': employee,
        'total_time': round(plan_ot['en_hours'], 2),
        'type': 'plan_ot_pending',
        'text_content': text_context_plan
      })
    leave_approved = self.env['en.technical.model'].read_group(
        [('employee_id', '=', employee), ('tech', '=', 'leave'),
         ('tech_type', '=', 'leave')], ['number'], ['date:day'])
    for leave in leave_approved:
      values.append({
        'date': leave['__range']['date']['from'],
        'employee_id': employee,
        'total_time': round(8 - leave['number'], 2),
        'type': 'leave_approved',
        'text_content': ''
      })
    # Lấy cả 2 trạng thái validate và draft
    leaves = self.env['hr.leave'].search([
      ('employee_id', '=', employee),
      ('state', 'in', ['confirm', 'draft'])
    ])

    for leave in leaves:
      # Lặp qua từng ngày trong khoảng từ date_from -> date_to
      for day in date_utils.date_range(leave.date_from, leave.date_to,
                                       relativedelta(days=1)):
        # day bây giờ là datetime
        day_start = datetime.combine(day.date(), time.min)
        day_end = datetime.combine(day.date(), time.max)

        overlap_start = max(leave.date_from, day_start)
        overlap_end = min(leave.date_to, day_end)

        if overlap_end <= overlap_start:
          continue

        overlap_hours = (overlap_end - overlap_start).total_seconds() / 3600.0
        total_time = 8.0 if overlap_hours >= 8.0 else overlap_hours

        values.append({
          'date': day.date(),  # chỉ lấy ngày khi lưu
          'employee_id': employee,
          'total_time': total_time,
          'type': f'leave_{leave.state}',
          'text_content': '',
        })

    leave_holiday = self.env['resource.calendar.leaves'].search(
        [('is_holiday', '=', True)])
    for holiday in leave_holiday:
      for date_step in date_utils.date_range(holiday.date_from, holiday.date_to,
                                             relativedelta(days=1)):
        date_step = (datetime.combine(date_step, time.min) + relativedelta(
          hours=7)).date()
        values.append({
          'date': date_step,
          'employee_id': employee,
          'total_time': 8,
          'type': 'leave_holiday',
          'text_content': ''
        })

    self.create(values)


