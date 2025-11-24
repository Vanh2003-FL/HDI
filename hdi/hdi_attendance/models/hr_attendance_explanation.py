# -*- coding: utf-8 -*-
from odoo import models, fields, api, _, Command
from odoo.exceptions import ValidationError, UserError
from datetime import date, datetime
from dateutil.relativedelta import relativedelta


class HrAttendanceExplanation(models.Model):
    _name = 'hr.attendance.explanation'
    _description = 'Attendance Explanation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'explanation_date desc, id desc'
    
    name = fields.Char(
        string='Số tham chiếu',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Nhân viên',
        required=True,
        default=lambda self: self.env.user.employee_id
    )
    employee_barcode = fields.Char(
        string='Mã nhân viên',
        related='employee_id.barcode',
        store=True
    )
    submission_type_id = fields.Many2one(
        'submission.type',
        string='Loại giải trình',
        required=True
    )
    submission_code = fields.Char(
        related='submission_type_id.code',
        string='Mã loại',
        store=True
    )
    used_explanation_date = fields.Boolean(
        related='submission_type_id.used_explanation_date',
        string='Sử dụng ngày giải trình',
        store=True
    )
    hr_attendance_id = fields.Many2one(
        'hr.attendance',
        string='Ngày điều chỉnh',
        domain="[('employee_id', '=', employee_id)]"
    )
    explanation_date = fields.Date(
        string='Ngày giải trình',
        tracking=True,
        required=True
    )
    
    # Details
    line_ids = fields.One2many(
        'hr.attendance.explanation.detail',
        'explanation_id',
        string='Chi tiết điều chỉnh'
    )
    
    # Explanation
    explanation_reason = fields.Text(string='Lý do giải trình', required=True)
    attachment_ids = fields.Many2many(
        'ir.attachment',
        string='Tài liệu đính kèm'
    )
    
    # Approval
    state = fields.Selection([
        ('new', 'Mới'),
        ('to_approve', 'Đã gửi duyệt'),
        ('approved', 'Đã duyệt'),
        ('refuse', 'Từ chối'),
        ('cancel', 'Đã hủy'),
    ], string='Trạng thái', default='new', tracking=True, required=True)
    
    approver_ids = fields.One2many(
        'hr.attendance.explanation.approver',
        'explanation_id',
        string='Người phê duyệt'
    )
    
    refusal_reason = fields.Text(string='Lý do từ chối')
    
    # For missing attendance (MA)
    missing_hr_attendance_id = fields.Many2one(
        'hr.attendance',
        string='Bản ghi chấm công bổ sung',
        readonly=True
    )
    
    # Computed fields
    check_need_approve = fields.Boolean(
        string='Cần phê duyệt',
        compute='_compute_check_need_approve'
    )
    condition_visible_button_refuse_approve = fields.Boolean(
        string='Hiển thị nút duyệt/từ chối',
        compute='compute_condition_visible_button_refuse_approve'
    )
    
    @api.depends('employee_id', 'hr_attendance_id')
    def _compute_check_need_approve(self):
        """Check if current user can approve"""
        for rec in self:
            rec.check_need_approve = False
            if rec.employee_id and rec.employee_id.parent_id:
                # User is manager of employee
                if rec.employee_id.parent_id.user_id == self.env.user:
                    rec.check_need_approve = True
    
    def compute_condition_visible_button_refuse_approve(self):
        """Check if approve/refuse buttons should be visible"""
        for rec in self:
            rec.condition_visible_button_refuse_approve = rec.check_need_approve
    
    @api.depends('employee_id', 'hr_attendance_id')
    def create_name(self):
        """Generate name for explanation"""
        for rec in self:
            if rec.employee_id and rec.explanation_date:
                rec.name = f"GT-{rec.employee_id.barcode or rec.employee_id.id}-{rec.explanation_date}"
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('hr.attendance.explanation') or _('New')
        return super().create(vals_list)
    
    def send_approve(self):
        """Submit explanation for approval"""
        self.ensure_one()
        if self.state != 'new':
            raise UserError(_('Chỉ có thể gửi duyệt bản ghi ở trạng thái Mới.'))
        
        self.write({'state': 'to_approve'})
        self.apply_approver()
        
        # Send notification
        if self.employee_id.parent_id and self.employee_id.parent_id.user_id:
            self.message_post(
                body=_('Giải trình chấm công đã được gửi để phê duyệt.'),
                partner_ids=[self.employee_id.parent_id.user_id.partner_id.id]
            )
    
    def apply_approver(self):
        """Create approver records"""
        self.ensure_one()
        # Clear existing approvers
        self.approver_ids.unlink()
        
        # Add manager as approver
        if self.employee_id.parent_id and self.employee_id.parent_id.user_id:
            self.env['hr.attendance.explanation.approver'].create({
                'explanation_id': self.id,
                'user_id': self.employee_id.parent_id.user_id.id,
                'role_selection': 'manager',
                'status': 'pending',
            })
    
    def button_approve(self):
        """Approve explanation"""
        self.ensure_one()
        if self.state != 'to_approve':
            raise UserError(_('Chỉ có thể phê duyệt bản ghi ở trạng thái Đã gửi duyệt.'))
        
        if not self.condition_visible_button_refuse_approve:
            raise UserError(_('Bạn không có quyền phê duyệt bản ghi này.'))
        
        # Apply changes to attendance
        attendance_values = {}
        
        for line in self.line_ids:
            if line.type == 'check_in':
                attendance_values['check_in'] = line.date
            elif line.type == 'check_out':
                attendance_values['check_out'] = line.date
        
        # Handle different submission types
        if self.submission_code == 'MA':  # Missing attendance
            # Create new attendance record
            attendance_values.update({
                'employee_id': self.employee_id.id,
                'en_location_id': self.employee_id.work_location_id.id,
                'en_missing_attendance': True,
            })
            
            if not self.missing_hr_attendance_id:
                self.missing_hr_attendance_id = self.env['hr.attendance'].create(attendance_values)
            else:
                self.missing_hr_attendance_id.sudo().write(attendance_values)
        else:
            # Update existing attendance
            if self.attendance_id and attendance_values:
                self.attendance_id.sudo().write(attendance_values)
        
        # Update state
        self.write({'state': 'approved'})
        
        # Update approver status
        for approver in self.approver_ids:
            if approver.user_id == self.env.user:
                approver.status = 'approved'
        
        # Send notification
        self.message_post(
            body=_('Giải trình chấm công đã được phê duyệt.'),
            partner_ids=[self.employee_id.user_id.partner_id.id]
        )
    
    def mass_button_approve(self):
        """Mass approve explanations"""
        for rec in self:
            if rec.state != 'to_approve':
                raise UserError(_('Chỉ có thể phê duyệt bản ghi ở trạng thái Đã gửi duyệt\n%s') % rec.name)
            if not rec.condition_visible_button_refuse_approve:
                raise UserError(_('Bạn không được phép phê duyệt bản ghi %s') % rec.name)
            rec.button_approve()
    
    def button_refuse(self):
        """Open wizard to refuse explanation"""
        self.ensure_one()
        return {
            'name': _('Từ chối giải trình'),
            'type': 'ir.actions.act_window',
            'res_model': 'reason.for.refuse.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_explanation_id': self.id,
            },
        }
    
    def mass_button_refuse(self):
        """Mass refuse explanations"""
        for rec in self:
            if rec.state != 'to_approve':
                raise UserError(_('Chỉ có thể từ chối bản ghi ở trạng thái Đã gửi duyệt\n%s') % rec.name)
            if not rec.condition_visible_button_refuse_approve:
                raise UserError(_('Bạn không được phép từ chối bản ghi %s') % rec.name)
    
    def button_draft(self):
        """Reset to new"""
        self.ensure_one()
        if self.create_uid != self.env.user and not self.env.user.has_group('base.group_system'):
            raise UserError(_('Chỉ người tạo hoặc Administrator mới có thể chuyển về Mới!'))
        
        self.write({
            'state': 'new',
            'approver_ids': [(5, 0, 0)],
        })
    
    def button_cancel(self):
        """Cancel explanation"""
        self.ensure_one()
        self.write({'state': 'cancel'})
    
    @api.constrains('employee_id', 'attendance_id', 'line_ids', 'explanation_date', 'submission_type_id')
    def check_limit_explanation(self):
        """Validate explanation limits and constraints"""
        en_max_attendance_request_count = int(
            self.env['ir.config_parameter'].sudo().get_param('en_max_attendance_request_count', 3)
        )
        en_attendance_request_start = int(
            self.env['ir.config_parameter'].sudo().get_param('en_attendance_request_start', 25)
        )
        
        for rec in self:
            today = fields.Date.today()
            day = today.day
            start_date = today.replace(day=en_attendance_request_start)
            if day < en_attendance_request_start:
                start_date = start_date - relativedelta(months=1)
            
            # Check if explanation date is valid
            if rec.explanation_date and rec.explanation_date < start_date:
                raise UserError(
                    _('Bạn chỉ được phép giải trình từ ngày %s') % start_date.strftime('%d/%m/%Y')
                )
            
            # Validate time fields
            time_check_in = rec.line_ids.filtered(lambda x: x.type == 'check_in').time
            time_check_out = rec.line_ids.filtered(lambda x: x.type == 'check_out').time
            
            if time_check_in and time_check_out and time_check_in > time_check_out:
                raise UserError(_('Giá trị mới Check in phải nhỏ hơn Check out'))
            
            # Check for missing attendance (MA)
            if rec.submission_code == 'MA':
                if not time_check_in or not time_check_out:
                    raise UserError(_('Bạn cần chọn cả giá trị Check in và Check out'))
                if not rec.explanation_date:
                    raise UserError(_('Bạn cần chọn Ngày giải trình chấm công'))
                if self.env['hr.attendance'].sudo().search_count([
                    ('employee_id', '=', rec.employee_id.id),
                    ('date', '=', rec.explanation_date)
                ]):
                    raise UserError(
                        _('Bạn đã chấm công cho ngày %s') % rec.explanation_date.strftime('%d/%m/%Y')
                    )
            
            # Check limit explanation count
            if not rec.submission_type_id.mark_count:
                continue
            
            date_check = rec.attendance_id.date if rec.attendance_id else rec.explanation_date
            if not date_check:
                continue
            
            if date_check.day < en_attendance_request_start:
                date_start = date_check.replace(day=en_attendance_request_start) - relativedelta(months=1)
                date_end = date_check.replace(day=en_attendance_request_start) - relativedelta(days=1)
            else:
                date_start = date_check.replace(day=en_attendance_request_start)
                date_end = (date_start + relativedelta(months=1)).replace(day=en_attendance_request_start) - relativedelta(days=1)
            
            explanation_count = len(set(self.search([
                ('employee_id', '=', rec.employee_id.id),
                ('submission_type_id.mark_count', '=', True),
                ('state', 'not in', ['refuse', 'cancel']),
                ('explanation_date', '>=', date_start),
                ('explanation_date', '<=', date_end)
            ]).mapped('explanation_date')))
            
            if 0 < en_max_attendance_request_count < explanation_count:
                raise UserError(
                    _('Bạn đã có %s giải trình chấm công trong tháng này. Vui lòng liên hệ nhân sự để được hỗ trợ.') 
                    % en_max_attendance_request_count
                )
    
    @api.ondelete(at_uninstall=True)
    def _unlink_if_draft(self):
        """Only allow delete if state is new"""
        for rec in self:
            if rec.state != 'new':
                raise UserError(_('Bạn chỉ xoá được bản ghi ở trạng thái Mới'))


class HrAttendanceExplanationApprover(models.Model):
    _name = 'hr.attendance.explanation.approver'
    _description = 'Attendance Explanation Approver'
    
    explanation_id = fields.Many2one(
        'hr.attendance.explanation',
        string='Giải trình',
        required=True,
        ondelete='cascade'
    )
    user_id = fields.Many2one('res.users', string='Người duyệt', required=True)
    role_selection = fields.Selection([
        ('manager', 'Quản lý'),
        ('hr', 'Nhân sự'),
    ], string='Vai trò', required=True)
    status = fields.Selection([
        ('pending', 'Chờ duyệt'),
        ('approved', 'Đã duyệt'),
        ('refused', 'Từ chối'),
    ], string='Trạng thái', default='pending', required=True)
