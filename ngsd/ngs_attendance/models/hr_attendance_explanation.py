from odoo import fields, models, api, Command, exceptions, _
from datetime import date, datetime

from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval
from dateutil.relativedelta import relativedelta
from odoo.tools.float_utils import float_round


class HrAttendanceExplanationDetail(models.Model):
    _name = 'hr.attendance.explanation.detail'
    _description = 'Chi tiết giải trình chấm công'

    explanation_id = fields.Many2one(string='Giải trình chấm công', comodel_name='hr.attendance.explanation', required=True, ondelete='cascade')
    type = fields.Selection(string='Cần điều chỉnh', selection=[('check_in', 'Check in'), ('check_out', 'Check out')], required=True)
    date = fields.Datetime(string='Giá trị mới', required=False)
    time = fields.Float(string='Thời gian thực tế', required=True, compute=False, store=True, readonly=False)

    @api.constrains('explanation_id', 'type')
    def _constrains_order_n_type(self):
        if any(rec.search_count([('explanation_id', '=', rec.explanation_id.id), ('type', '=', rec.type)]) > 1 for rec in self):
            raise exceptions.ValidationError('Chỉ có thể chọn 1 giá trị Check in/Check out')

    @api.constrains('time')
    def check_valid_hour(self):
        for rec in self:
            if not (0.01 <= rec.time <= 23.99):
                raise UserError('Giá trị mới không hợp lệ (00:01-23:59)')


class HrAttendanceExplanation(models.Model):
    _name = 'hr.attendance.explanation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Giải trình chấm công'

    name = fields.Char(string='Tên giải trình', compute='create_name', compute_sudo=True)
    employee_id = fields.Many2one('hr.employee', string='Nhân viên', required=True, default=lambda self: self.env.user.employee_id, ondelete='cascade')
    employee_barcode = fields.Char(string='Mã nhân viên', related='employee_id.barcode', store=True)
    en_area_id = fields.Many2one(related='employee_id.en_area_id')
    submission_type_id = fields.Many2one('submission.type', string='Loại giải trình', required=True)
    hr_attendance_id = fields.Many2one('hr.attendance', string='Ngày điều chỉnh', required=False, domain="[('employee_id','=',employee_id)]")
    missing_hr_attendance_id = fields.Many2one('hr.attendance', string='Bản chấm công')
    explanation_reason = fields.Text(string='Lý do giải trình')
    approver_ids = fields.One2many('approval.approver', 'hr_attendance_explanation_id', string="Thông tin phê duyệt")
    state = fields.Selection([('new', 'Mới'), ('to_approve', 'Đã gửi duyệt'), ('approved', 'Đã duyệt'), ('refuse', 'Từ chối'), ('cancel', 'Hủy')], string='Trạng thái', default='new')
    condition_visible_button_refuse_aprrove = fields.Boolean(compute='compute_condition_visible_button_refuse_aprrove', string='điều kiện hiện button duyệt và từ chối')
    reason_for_refuse = fields.Text(string='Lý do từ chối', readonly=True)
    check_need_approve = fields.Boolean(string='bộ lọc cần phê duyệt', compute='compute_check_need_approve', search='_search_check_need_approve')

    line_ids = fields.One2many(string='Chi tiết giải trình chấm công', comodel_name='hr.attendance.explanation.detail', inverse_name='explanation_id')
    explanation_date = fields.Date(string='Ngày giải trình', compute='_get_explanation_date', store=True, readonly=False, tracking=True, required=1)

    @api.depends('hr_attendance_id', 'submission_type_id')
    def _get_explanation_date(self):
        for rec in self:
            explanation_date = False
            if not rec.submission_type_id.used_explanation_date and rec.hr_attendance_id:
                explanation_date = rec.hr_attendance_id.date
            rec.explanation_date = explanation_date

    @api.model
    def _search_check_need_approve(self, operator, operand):
        if operator not in ['=']:
            raise exceptions.UserError(_('Invalid domain operator %s', operator))
        matching_record = self.env['approval.approver'].search([('status', '=', 'pending'), ('user_id', '=', self.env.user.id), ('hr_attendance_explanation_id', '!=', False), ('hr_attendance_explanation_id.state', '=', 'to_approve')]).hr_attendance_explanation_id
        if operand:
            return [('id', 'in', matching_record.ids)]
        else:
            return [('id', 'not in', matching_record)]

    @api.depends('approver_ids', 'state', 'approver_ids.status', 'approver_ids.user_id')
    def compute_check_need_approve(self):
        for rec in self:
            if rec.state == 'to_approve' and rec.approver_ids.filtered(lambda x: x.status == 'pending' and x.user_id == self.env.user):
                rec.check_need_approve = True
            else:
                 rec.check_need_approve = False

    @api.depends('approver_ids.status')
    def compute_condition_visible_button_refuse_aprrove(self):
        for rec in self:
            rec.condition_visible_button_refuse_aprrove = self.approver_ids.filtered(lambda approver: approver.status == 'pending').sorted(key=lambda x:x.sequence)[:1].user_id == self.env.user if self.approver_ids else False

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super().fields_get(allfields, attributes)
        for fname in res:
            if res.get(fname).get('readonly'):
                continue
            states = {
                'new': [('readonly', False)],
                'to_approve': [('readonly', True)],
                'approved': [('readonly', True)],
                'refuse': [('readonly', True)],
                'cancel': [('readonly', True)],
            }
            res[fname].update({'states': states})
        return res

    @api.depends('employee_id', 'explanation_date')
    def create_name(self):
        for rec in self:
            rec.name = f'{rec.employee_id.name} giải trình công ngày {rec.explanation_date.strftime("%d/%m/%Y") if rec.explanation_date else ""}'

    submission_code = fields.Char(related='submission_type_id.code', store=True)
    used_explanation_date = fields.Boolean(related='submission_type_id.used_explanation_date', store=True)
    ts_ids = fields.One2many('account.analytic.line', 'explanation_id')

    def action_view_timesheet(self):
        if not self.ts_ids:
            return
        return self.open_form_or_tree_view(action='hr_timesheet.timesheet_action_all', records=self.ts_ids)

    show_action_view_timesheet = fields.Boolean(compute='_get_action_view_timesheet')

    @api.depends('ts_ids', 'state')
    def _get_action_view_timesheet(self):
        for rec in self:
            if rec.ts_ids and rec.submission_code in ['TSDA', 'TSNDA']:
                rec.show_action_view_timesheet = True
            else:
                rec.show_action_view_timesheet = False

    def float_to_relativedelta(self, float_hour):
        if float_hour == 24:
            float_hour = 23.9999
        minute = (float_hour % 1) * 60
        second = (minute % 1) * 60
        return relativedelta(hour=int(float_hour), minute=int(minute), second=int(second), microsecond=0)

    def send_approve(self):
        self.ensure_one()
        if self.create_uid != self.env.user:
            raise UserError('Chỉ người giải trình mới có thể gửi phê duyệt!')
        if self.explanation_date > fields.Date.Date.Date.context_today(self):
            raise UserError('Không thể tạo giải trình trong tương lai!')
        if self.submission_code in ['TSDA', 'TSNDA']:
            if self.ts_ids:
                return
            return {
                'type': 'ir.actions.act_window',
                'name': 'Tạo timesheet giải trình',
                'res_model': 'explanation.task.timesheet',
                'view_mode': 'form',
                'context': {
                    'default_explanation_id': self.id,
                    'default_type': self.submission_code,
                },
                'target': 'new',
            }
        else:
            if not self.line_ids:
                raise exceptions.ValidationError('Bạn cần chọn giá trị điều chỉnh mới!')
            date_check_out = False
            if self.submission_type_id.code != 'MA':
                date_check_out = self.hr_attendance_id.check_out
                # check_date = self.hr_attendance_id.check_in or self.hr_attendance_id.check_out
                # for line in self.line_ids:
                #     if line.date and check_date and (line.date + relativedelta(hours=7)).date() != (check_date + relativedelta(hours=7)).date():
                #         raise UserError('Giá trị mới phải cùng ngày với ngày chấm công')
            else:
                time_check_out = self.line_ids.filtered(lambda x: x.type == 'check_out').time
                time_check_in = self.line_ids.filtered(lambda x: x.type == 'check_in').time
                if not time_check_out or not time_check_in:
                    raise UserError('Bạn cần chọn cả giá trị Check in và Check out')
                if self.explanation_date and time_check_out:
                    date_check_out = self.explanation_date + self.float_to_relativedelta(time_check_out) - relativedelta(hours=7)
            en_max_attendance_request = float(self.env['ir.config_parameter'].sudo().get_param('en_max_attendance_request'))
            time_now = datetime.now()
            if en_max_attendance_request >= 0 and date_check_out and date_check_out + relativedelta(hours=en_max_attendance_request) <= time_now:
                raise UserError('Đã quá thời gian cho phép giải trình')
        self.apply_approver()

    def apply_approver(self):
        self._new_compute_approver_ids()
        user = self.mapped('approver_ids').filtered(lambda approver: approver.status == 'new').sorted(key=lambda approve: approve.sequence)[:1]
        self.send_notify('Bạn có bản ghi Giải trình cần phê duyệt. Bấm tại đây để xem chi tiết.', user.user_id)
        approvers = self.mapped('approver_ids').filtered(lambda approver: approver.status == 'new')
        approvers.write({'status': 'pending'})
        self.write({'state': 'to_approve'})

    def get_flow_domain(self):
        return [('model', '=', self._name),'|', ('block_ids', '=', False), ('block_ids', '=', self.employee_id.en_block_id.id), '|',
                ('department_ids', '=', False), ('department_ids', '=', self.employee_id.department_id.id), '|',
                ('en_department_ids', '=', False), ('en_department_ids', '=', self.employee_id.en_department_id.id)]

    def _new_compute_approver_ids(self):
        self.ensure_one()
        request = self.sudo()
        if not request.ts_ids:
            processes = self.env['office.approve.flow'].search(request.get_flow_domain(), order='id desc')
            approver_id_vals = []
            for process in processes:
                if not request.filtered_domain(safe_eval(process.domain or '[]')):
                    continue
                for rule in process.rule_ids.sorted(lambda x: x.visible_sequence):
                    approver_user_id = self.env['res.users']
                    visible_sequence = rule.visible_sequence
                    role_selection = False
                    if rule.type == 'person':
                        approver_user_id = rule.user_id
                        role_selection = rule.en_role_detail
                    if rule.type == 'role' and rule.role_selection:
                        employee = request.employee_id
                        role_selection_selection = dict(rule.fields_get(['role_selection'])['role_selection']['selection'])
                        if rule.role_selection == 'block':
                            approver_user_id = employee.en_block_id.en_project_implementation_id
                        if rule.role_selection == 'department':
                            approver_user_id = employee.department_id.manager_id.user_id
                        if rule.role_selection == 'en_department':
                            approver_user_id = employee.en_department_id.manager_id.user_id
                        if rule.role_selection == 'manager':
                            approver_user_id = employee.parent_id.user_id
                        role_selection = role_selection_selection.get(rule.role_selection)
                    if not approver_user_id:
                        continue
                    approver_id_vals.append(Command.create({
                        'user_id': approver_user_id.id,
                        'status': 'new',
                        'role_selection': role_selection,
                        'sequence': visible_sequence,
                    }))
                break
            if not approver_id_vals:
                raise UserError('Không tìm thấy quy trình duyệt hoặc người duyệt tương ứng')
        else:
            approver_id_vals = []
            for idx, ts in enumerate(request.ts_ids, start=1):
                approver_id_vals.append(Command.create({
                    'user_id': ts.en_approver_id.id,
                    'status': 'new',
                    'sequence': idx,
                }))
        approver_id_vals = [(5, 0, 0)] + approver_id_vals
        request.update({'approver_ids': approver_id_vals})

    def mass_button_approve(self):
        for rec in self.sudo():
            if rec.state != 'to_approve':
                raise UserError('Chỉ có thể Duyệt bản ghi ở trạng thái Đã gửi duyệt\n%s'%rec.name)
            if not rec.condition_visible_button_refuse_aprrove:
                raise UserError('Bạn không được phép Duyệt bản ghi %s'%rec.name)
            rec.button_approve()

    def button_approve(self):
        for rec in self.sudo():
            approver = rec.mapped('approver_ids').filtered(lambda approver: approver.user_id == self.env.user)
            approver.write({'status': 'approved'})
            user = rec.mapped('approver_ids').filtered(lambda approver: approver.status == 'pending').sorted(key=lambda approve: approve.sequence)[:1]
            rec.send_notify('Bạn có bản ghi Giải trình cần phê duyệt. Bấm tại đây để xem chi tiết.', user.user_id)
            if all(approver_ids.status == 'approved' for approver_ids in rec.approver_ids):
                rec.write({'state': 'approved'})
                if rec.submission_code not in ['TSDA', 'TSNDA']:
                    attendance_values = {'en_missing_attendance': False}
                    for line in rec.line_ids:
                        convert_date = rec.explanation_date + rec.float_to_relativedelta(line.time) - relativedelta(hours=7)
                        attendance_values.update({line.type: convert_date})
                    hr_attendance_id = rec.hr_attendance_id
                    if rec.submission_type_id.code == 'MA':
                        attendance_values['employee_id'] = rec.employee_id.id
                        attendance_values['en_location_id'] = rec.employee_id.work_location_id.id
                        attendance_values['en_location_checkout_id'] = rec.employee_id.work_location_id.id
                        if not rec.missing_hr_attendance_id:
                            rec.missing_hr_attendance_id = self.env['hr.attendance'].with_user(rec.employee_id.user_id or self.env.user).create(attendance_values)
                        else:
                            rec.missing_hr_attendance_id.sudo().write(attendance_values)
                        hr_attendance_id = rec.missing_hr_attendance_id
                    else:
                        hr_attendance_id.sudo().write(attendance_values)
                    hr_attendance_id._compute_worked_hours()
                else:
                    rec.ts_ids.with_context(timesheet_from_explanation=True).sudo().write(dict(en_state='approved'))
                rec.send_notify('Bản ghi Giải trình của bạn đã được phê duyệt. Vui lòng bấm tại đây để xem chi tiết.', rec.employee_id.user_id)


    def mass_button_refuse(self):
        for rec in self.sudo():
            if rec.state != 'to_approve':
                raise UserError('Chỉ có thể Từ chối bản ghi ở trạng thái Đã gửi duyệt\n%s'%rec.name)
            if not rec.condition_visible_button_refuse_aprrove:
                raise UserError('Bạn không được phép Từ chối bản ghi %s'%rec.name)
            rec.button_refuse()

    def button_refuse(self):
        action = {
            'type': 'ir.actions.act_window',
            'name': 'Lý do từ chối',
            'res_model': 'reason.for.refuse.wizard',
            'view_mode': 'form',
            'context': {'default_hr_attendance_explanation_id': self.id},
            'target': 'new',
        }
        return action

    def button_cancel(self):
        self.write({
            'state': 'cancel'
        })

    @api.ondelete(at_uninstall=True)
    def _unlink_if_draft(self):
        for att in self:
            if att.state != 'new':
                raise UserError('Bạn chỉ xoá được bản ghi ở trạng thái Mới')

    @api.constrains('employee_id', 'hr_attendance_id', 'line_ids', 'explanation_date', 'submission_type_id')
    def check_limit_explanation(self):
        en_max_attendance_request_count = int(self.env['ir.config_parameter'].sudo().get_param('en_max_attendance_request_count'))
        en_attendance_request_start = int(self.env['ir.config_parameter'].sudo().get_param('en_attendance_request_start'))
        time_to_float = self.env['en.hr.overtime'].time_to_float
        for rec in self:
            today = fields.Date.Date.Date.context_today(self)
            day = today.day
            start_date = today + relativedelta(day=en_attendance_request_start)
            if day <= en_attendance_request_start:
                start_date -= relativedelta(months=1)
            if rec.explanation_date < start_date:
                raise UserError('Bạn chỉ được phép giải trình từ ngày %s' % start_date.strftime('%d/%m/%Y'))


            date_check = rec.hr_attendance_id.date
            time_check_in = rec.line_ids.filtered(lambda x: x.type == 'check_in').time
            time_check_out = rec.line_ids.filtered(lambda x: x.type == 'check_out').time
            if time_check_in and time_check_out and time_check_in > time_check_out:
                raise UserError('Giá trị mới Check in phải nhỏ hơn Check out')
            if time_check_in and not time_check_out and rec.hr_attendance_id.check_out and time_check_in > (time_to_float(rec.hr_attendance_id.check_out + relativedelta(hours=7))):
                raise UserError('Giá trị mới Check in phải nhỏ hơn Check out của bản ghi chấm công')
            if time_check_out and not time_check_in and rec.hr_attendance_id.check_in and (time_to_float(rec.hr_attendance_id.check_in + relativedelta(hours=7))) > time_check_out:
                raise UserError('Giá trị mới Check out phải lớn hơn Check in của bản ghi chấm công')

            if rec.submission_code == 'MA':
                if not time_check_in or not time_check_out:
                    raise UserError('Bạn cần chọn cả giá trị Check in và Check out')
                if not rec.explanation_date:
                    raise UserError('Bạn cần chọn Ngày giải trình chấm công')
                if self.env['hr.attendance'].sudo().search_count([('employee_id', '=', rec.employee_id.id), ('date', '=', rec.explanation_date)]):
                    raise UserError('Bạn đã chấm công cho ngày %s'%rec.explanation_date)
            if not rec.submission_type_id.mark_count:
                continue
            if rec.used_explanation_date:
                date_check = rec.explanation_date
            if date_check.day < en_attendance_request_start:
                date_start = date_check + relativedelta(day=en_attendance_request_start, months=-1)
                date_end = date_check + relativedelta(day=en_attendance_request_start, days=-1)
            else:
                date_start = date_check + relativedelta(day=en_attendance_request_start)
                date_end = date_check + relativedelta(day=en_attendance_request_start, months=1, days=-1)

            if 0 < en_max_attendance_request_count < len(set(self.search([
                ('employee_id', '=', rec.employee_id.id),
                ('submission_type_id.mark_count', '=', True),
                ('state', 'not in', ['refuse', 'cancel']),
                ('explanation_date', '>=', date_start),
                ('explanation_date', '<=', date_end)]).mapped('explanation_date'))):
                raise UserError('Bạn đã có %s giải trình chấm công trong tháng này. Vui lòng liên hệ nhân sự để được hỗ trợ.'%en_max_attendance_request_count)

    def button_draft(self):
        if self.create_uid != self.env.user and not self.env.user.has_group('base.group_system'):
            raise UserError('Chỉ người giải trình hoặc Administrator mới có thể chuyển về Mới!')
        if self.ts_ids:
            self.ts_ids.unlink()
        self.write({
            'state': 'new',
            'approver_ids': False,
        })


class SubmissionType(models.Model):
    _name = 'submission.type'
    _description = 'Loại giải trình'

    name = fields.Char(string='Loại giải trình', required=True)
    code = fields.Char(string='Mã')
    mark_count = fields.Boolean(string='Tính vào số lần giải trình', default=True)
    used_explanation_date = fields.Boolean(string='Sử dụng Ngày giải trình', default=False)