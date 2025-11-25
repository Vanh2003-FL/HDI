# -*- coding: utf-8 -*-
from odoo import models, fields, api, _, Command
from odoo.exceptions import ValidationError, UserError
from datetime import datetime
from dateutil.relativedelta import relativedelta


class HrAttendanceExplanation(models.Model):
    _name = 'hr.attendance.explanation'
    _description = 'Giải trình chấm công'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'explanation_date desc, id desc'
    
    name = fields.Char(string='Tên giải trình', compute='_compute_name', compute_sudo=True, store=True)
    employee_id = fields.Many2one('hr.employee', string='Nhân viên', required=True, 
                                   default=lambda self: self.env.user.employee_id, ondelete='cascade')
    employee_barcode = fields.Char(string='Mã nhân viên', related='employee_id.barcode', store=True)
    submission_type_id = fields.Many2one('submission.type', string='Loại giải trình', required=True)
    submission_code = fields.Char(related='submission_type_id.code', store=True)
    used_explanation_date = fields.Boolean(related='submission_type_id.used_explanation_date', store=True)
    hr_attendance_id = fields.Many2one('hr.attendance', string='Ngày điều chỉnh', 
                                        domain="[('employee_id', '=', employee_id)]")
    explanation_date = fields.Date(string='Ngày giải trình', compute='_compute_explanation_date',
                                    store=True, readonly=False, tracking=True, required=True)
    line_ids = fields.One2many('hr.attendance.explanation.detail', 'explanation_id', 
                                string='Chi tiết điều chỉnh')
    explanation_reason = fields.Text(string='Lý do giải trình', required=True)
    attachment_ids = fields.Many2many('ir.attachment', string='Tài liệu đính kèm')
    state = fields.Selection([('new', 'Mới'), ('to_approve', 'Đã gửi duyệt'), ('approved', 'Đã duyệt'),
                              ('refuse', 'Từ chối'), ('cancel', 'Hủy')], 
                             string='Trạng thái', default='new', tracking=True, required=True)
    approver_ids = fields.One2many('hr.attendance.explanation.approver', 'explanation_id', 
                                    string='Người phê duyệt')
    reason_for_refuse = fields.Text(string='Lý do từ chối', readonly=True)
    missing_hr_attendance_id = fields.Many2one('hr.attendance', string='Bản chấm công bổ sung', readonly=True)
    check_need_approve = fields.Boolean(string='Cần phê duyệt', compute='_compute_check_need_approve',
                                         search='_search_check_need_approve')
    condition_visible_button_refuse_approve = fields.Boolean(compute='_compute_condition_visible_button_refuse_approve')
    
    @api.depends('hr_attendance_id', 'submission_type_id', 'hr_attendance_id.date')
    def _compute_explanation_date(self):
        for rec in self:
            if not rec.submission_type_id.used_explanation_date and rec.hr_attendance_id:
                rec.explanation_date = rec.hr_attendance_id.date
            elif not rec.explanation_date:
                rec.explanation_date = fields.Date.today()
    
    @api.depends('employee_id', 'explanation_date')
    def _compute_name(self):
        for rec in self:
            if rec.employee_id and rec.explanation_date:
                rec.name = f'{rec.employee_id.name} giải trình công ngày {rec.explanation_date.strftime("%d/%m/%Y")}'
            else:
                rec.name = 'Giải trình chấm công'
    
    @api.model
    def _search_check_need_approve(self, operator, operand):
        if operator not in ['=', '!=']:
            raise UserError(_('Invalid operator'))
        matching = self.env['hr.attendance.explanation.approver'].search([
            ('state', '=', 'pending'), ('user_id', '=', self.env.user.id),
            ('explanation_id.state', '=', 'to_approve')
        ]).mapped('explanation_id')
        if (operator == '=' and operand) or (operator == '!=' and not operand):
            return [('id', 'in', matching.ids)]
        return [('id', 'not in', matching.ids)]
    
    @api.depends('approver_ids', 'approver_ids.state', 'state')
    def _compute_check_need_approve(self):
        for rec in self:
            rec.check_need_approve = bool(rec.state == 'to_approve' and 
                rec.approver_ids.filtered(lambda a: a.state == 'pending' and a.user_id == self.env.user))
    
    @api.depends('approver_ids', 'approver_ids.state')
    def _compute_condition_visible_button_refuse_approve(self):
        for rec in self:
            pending = rec.approver_ids.filtered(lambda a: a.state == 'pending').sorted('sequence')
            rec.condition_visible_button_refuse_approve = pending[0].user_id == self.env.user if pending else False
    
    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super().fields_get(allfields, attributes)
        for fname in res:
            if not res.get(fname).get('readonly'):
                res[fname]['states'] = {'new': [('readonly', False)], 'to_approve': [('readonly', True)],
                                         'approved': [('readonly', True)], 'refuse': [('readonly', True)],
                                         'cancel': [('readonly', True)]}
        return res
    
    def float_to_relativedelta(self, float_hour):
        if float_hour >= 24:
            float_hour = 23.9999
        h = int(float_hour)
        m = int((float_hour % 1) * 60)
        s = int(((float_hour % 1) * 60 % 1) * 60)
        return relativedelta(hours=h, minutes=m, seconds=s)
    
    def send_approve(self):
        self.ensure_one()
        if self.create_uid != self.env.user:
            raise UserError(_('Chỉ người tạo mới có thể gửi phê duyệt!'))
        if self.explanation_date > fields.Date.today():
            raise UserError(_('Không thể giải trình trong tương lai!'))
        if not self.line_ids:
            raise UserError(_('Bạn cần thêm chi tiết điều chỉnh!'))
        
        if self.submission_code == 'MA':
            check_in = self.line_ids.filtered(lambda x: x.type == 'check_in')
            check_out = self.line_ids.filtered(lambda x: x.type == 'check_out')
            if not check_in or not check_out:
                raise UserError(_('Cần có cả Check in và Check out'))
            if check_in.time >= check_out.time:
                raise UserError(_('Check in phải nhỏ hơn Check out'))
            if self.env['hr.attendance'].search([('employee_id', '=', self.employee_id.id),
                                                   ('date', '=', self.explanation_date)], limit=1):
                raise UserError(_('Đã chấm công ngày này'))
        
        en_max = float(self.env['ir.config_parameter'].sudo().get_param('en_max_attendance_request', 0))
        if en_max > 0:
            check_out_time = None
            if self.submission_code == 'MA':
                co = self.line_ids.filtered(lambda x: x.type == 'check_out')
                if co:
                    check_out_time = self.explanation_date + self.float_to_relativedelta(co.time)
            elif self.hr_attendance_id and self.hr_attendance_id.check_out:
                check_out_time = self.hr_attendance_id.check_out
            if check_out_time and (datetime.now() - check_out_time).total_seconds() / 3600 > en_max:
                raise UserError(_('Đã quá thời gian giải trình'))
        
        self.apply_approver()
        self.write({'state': 'to_approve'})
        if self.approver_ids:
            self.message_post(body=_('Giải trình chấm công cần phê duyệt.'),
                            partner_ids=[self.approver_ids.sorted('sequence')[0].user_id.partner_id.id],
                            message_type='notification')
    
    def apply_approver(self):
        self.ensure_one()
        self.approver_ids.unlink()
        if self.employee_id.parent_id and self.employee_id.parent_id.user_id:
            self.env['hr.attendance.explanation.approver'].create({
                'explanation_id': self.id, 'user_id': self.employee_id.parent_id.user_id.id,
                'role_selection': 'manager', 'state': 'pending', 'sequence': 10,
            })
    
    def button_approve(self):
        self.ensure_one()
        if self.state != 'to_approve':
            raise UserError(_('Chỉ phê duyệt ở trạng thái Đã gửi duyệt'))
        if not self.condition_visible_button_refuse_approve:
            raise UserError(_('Không có quyền phê duyệt'))
        
        approver = self.approver_ids.filtered(lambda a: a.user_id == self.env.user and a.state == 'pending')
        if approver:
            approver.write({'state': 'approved', 'approval_date': fields.Datetime.now()})
        
        if all(a.state == 'approved' for a in self.approver_ids):
            self._action_approve_complete()
        else:
            next_app = self.approver_ids.filtered(lambda a: a.state == 'pending').sorted('sequence')
            if next_app:
                self.message_post(body=_('Giải trình chấm công cần phê duyệt.'),
                                partner_ids=[next_app[0].user_id.partner_id.id], message_type='notification')
    
    def _action_approve_complete(self):
        self.ensure_one()
        att_vals = {}
        for line in self.line_ids:
            att_vals[line.type] = self.explanation_date + self.float_to_relativedelta(line.time) - relativedelta(hours=7)
        
        if self.submission_code == 'MA':
            att_vals.update({'employee_id': self.employee_id.id, 'en_missing_attendance': True,
                           'en_location_id': self.employee_id.work_location_id.id if self.employee_id.work_location_id else False})
            if not self.missing_hr_attendance_id:
                self.missing_hr_attendance_id = self.env['hr.attendance'].sudo().create(att_vals)
            else:
                self.missing_hr_attendance_id.sudo().write(att_vals)
            self.missing_hr_attendance_id.sudo()._compute_worked_hours()
        elif self.hr_attendance_id and att_vals:
            self.hr_attendance_id.sudo().write(att_vals)
            self.hr_attendance_id.sudo()._compute_worked_hours()
        
        self.write({'state': 'approved'})
        if self.employee_id.user_id:
            self.message_post(body=_('Giải trình đã được phê duyệt.'),
                            partner_ids=[self.employee_id.user_id.partner_id.id], message_type='notification')
    
    def mass_button_approve(self):
        for rec in self:
            if rec.state != 'to_approve':
                raise UserError(_('Chỉ phê duyệt ở trạng thái Đã gửi duyệt\n%s') % rec.name)
            if not rec.condition_visible_button_refuse_approve:
                raise UserError(_('Không có quyền phê duyệt %s') % rec.name)
            rec.button_approve()
    
    def button_refuse(self):
        self.ensure_one()
        if self.state != 'to_approve':
            raise UserError(_('Chỉ từ chối ở trạng thái Đã gửi duyệt'))
        if not self.condition_visible_button_refuse_approve:
            raise UserError(_('Không có quyền từ chối'))
        return {'name': _('Lý do từ chối'), 'type': 'ir.actions.act_window',
                'res_model': 'reason.for.refuse.wizard', 'view_mode': 'form',
                'context': {'default_explanation_id': self.id}, 'target': 'new'}
    
    def mass_button_refuse(self):
        for rec in self:
            if rec.state != 'to_approve':
                raise UserError(_('Chỉ từ chối ở trạng thái Đã gửi duyệt\n%s') % rec.name)
            if not rec.condition_visible_button_refuse_approve:
                raise UserError(_('Không có quyền từ chối %s') % rec.name)
        return {'name': _('Lý do từ chối'), 'type': 'ir.actions.act_window',
                'res_model': 'reason.for.refuse.wizard', 'view_mode': 'form',
                'context': {'default_explanation_ids': [(6, 0, self.ids)]}, 'target': 'new'}
    
    def button_cancel(self):
        for rec in self:
            if rec.state not in ['new', 'refuse']:
                raise UserError(_('Chỉ hủy ở trạng thái Mới hoặc Từ chối'))
            rec.write({'state': 'cancel'})
    
    def button_draft(self):
        self.ensure_one()
        if self.create_uid != self.env.user and not self.env.user.has_group('base.group_system'):
            raise UserError(_('Chỉ người tạo hoặc Admin mới được chuyển về Mới'))
        self.write({'state': 'new', 'reason_for_refuse': False})
        self.approver_ids.unlink()
    
    @api.constrains('explanation_date')
    def _check_explanation_date(self):
        for rec in self:
            if rec.explanation_date and rec.explanation_date > fields.Date.today():
                raise ValidationError(_('Không thể giải trình trong tương lai'))
    
    @api.constrains('employee_id', 'explanation_date', 'submission_type_id', 'line_ids')
    def _check_limit_explanation(self):
        count_max = int(self.env['ir.config_parameter'].sudo().get_param('en_max_attendance_request_count', 3))
        start_day = int(self.env['ir.config_parameter'].sudo().get_param('en_attendance_request_start', 25))
        
        for rec in self:
            if rec.state != 'new':
                continue
            
            today = fields.Date.today()
            if today.day < start_day:
                period_start = today.replace(day=start_day) - relativedelta(months=1)
            else:
                period_start = today.replace(day=start_day)
            
            if rec.explanation_date and rec.explanation_date < period_start:
                raise ValidationError(_('Chỉ giải trình từ ngày %s') % period_start.strftime('%d/%m/%Y'))
            
            ci = rec.line_ids.filtered(lambda x: x.type == 'check_in')
            co = rec.line_ids.filtered(lambda x: x.type == 'check_out')
            if ci and co and ci.time >= co.time:
                raise ValidationError(_('Check in phải nhỏ hơn Check out'))
            
            if not rec.submission_type_id.mark_count:
                continue
            
            date_check = rec.hr_attendance_id.date if rec.hr_attendance_id else rec.explanation_date
            if not date_check:
                continue
            
            if date_check.day < start_day:
                ds = date_check.replace(day=start_day) - relativedelta(months=1)
                de = date_check.replace(day=start_day) - relativedelta(days=1)
            else:
                ds = date_check.replace(day=start_day)
                de = (ds + relativedelta(months=1)).replace(day=start_day) - relativedelta(days=1)
            
            exp_count = len(set(self.search([('employee_id', '=', rec.employee_id.id),
                ('submission_type_id.mark_count', '=', True), ('state', 'not in', ['refuse', 'cancel']),
                ('explanation_date', '>=', ds), ('explanation_date', '<=', de),
                ('id', '!=', rec.id)]).mapped('explanation_date')))
            
            if 0 < count_max <= exp_count:
                raise ValidationError(_('Đã có %s giải trình trong chu kỳ') % count_max)
    
    @api.onchange('submission_type_id')
    def _onchange_submission_type_id(self):
        if self.submission_type_id:
            self.line_ids = [(5, 0, 0)]
    
    @api.onchange('hr_attendance_id')
    def _onchange_hr_attendance_id(self):
        if self.hr_attendance_id and not self.submission_type_id.used_explanation_date:
            self.explanation_date = self.hr_attendance_id.date
    
    @api.ondelete(at_uninstall=True)
    def _unlink_if_draft(self):
        for rec in self:
            if rec.state != 'new':
                raise UserError(_('Chỉ xóa ở trạng thái Mới'))


class HrAttendanceExplanationApprover(models.Model):
    _name = 'hr.attendance.explanation.approver'
    _description = 'Người phê duyệt giải trình'
    _order = 'sequence, id'
    
    explanation_id = fields.Many2one('hr.attendance.explanation', string='Giải trình', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Thứ tự', default=10)
    user_id = fields.Many2one('res.users', string='Người duyệt', required=True)
    role_selection = fields.Selection([('manager', 'Quản lý'), ('hr_manager', 'HR'),
                                        ('department_head', 'Trưởng phòng'), ('director', 'Giám đốc')],
                                       string='Vai trò', required=True)
    state = fields.Selection([('new', 'Mới'), ('pending', 'Chờ duyệt'),
                              ('approved', 'Đã duyệt'), ('refuse', 'Từ chối')],
                             string='Trạng thái', default='new', required=True)
    approval_date = fields.Datetime(string='Ngày duyệt', readonly=True)
    comment = fields.Text(string='Nhận xét')
