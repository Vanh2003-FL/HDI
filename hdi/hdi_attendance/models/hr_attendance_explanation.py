# -*- coding: utf-8 -*-
from odoo import models, fields, api, Command, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime
from dateutil.relativedelta import relativedelta


class HrAttendanceExplanation(models.Model):
    _name = 'hr.attendance.explanation'
    _description = 'Attendance Explanation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'explanation_date desc, id desc'
    
    # === BASIC INFO ===
    name = fields.Char(
        string='Tên giải trình',
        compute='_compute_name',
        store=True,
        compute_sudo=True
    )
    
    employee_id = fields.Many2one(
        'hr.employee',
        string='Nhân viên',
        required=True,
        default=lambda self: self.env.user.employee_id,
        ondelete='cascade',
        tracking=True
    )
    
    employee_barcode = fields.Char(
        string='Mã nhân viên',
        related='employee_id.barcode',
        store=True
    )
    
    # === DATE & TIME ===
    explanation_date = fields.Date(
        string='Ngày giải trình',
        required=True,
        tracking=True,
        default=fields.Date.context_today
    )
    
    submission_type_id = fields.Many2one(
        'submission.type',
        string='Loại giải trình',
        required=True,
        tracking=True
    )
    
    submission_code = fields.Char(
        related='submission_type_id.code',
        store=True,
        string='Mã loại giải trình'
    )
    
    used_explanation_date = fields.Boolean(
        related='submission_type_id.used_explanation_date',
        store=True
    )
    
    # === ATTENDANCE RECORDS ===
    hr_attendance_id = fields.Many2one(
        'hr.attendance',
        string='Ngày điều chỉnh',
        domain="[('employee_id','=',employee_id)]",
        tracking=True
    )
    
    missing_hr_attendance_id = fields.Many2one(
        'hr.attendance',
        string='Bản chấm công thiếu',
        help='Dùng cho trường hợp giải trình thiếu chấm công (MA)'
    )
    
    # === DETAIL LINES ===
    line_ids = fields.One2many(
        'hr.attendance.explanation.detail',
        'explanation_id',
        string='Chi tiết giải trình',
        copy=True
    )
    
    # === EXPLANATION ===
    explanation_reason = fields.Text(
        string='Lý do giải trình',
        required=True,
        tracking=True
    )
    
    attachment_ids = fields.Many2many(
        'ir.attachment',
        string='Tài liệu đính kèm'
    )
    
    # === APPROVAL WORKFLOW ===
    state = fields.Selection([
        ('new', 'Mới'),
        ('to_approve', 'Đã gửi duyệt'),
        ('approved', 'Đã duyệt'),
        ('refuse', 'Từ chối'),
        ('cancel', 'Hủy'),
    ], string='Trạng thái', default='new', required=True, tracking=True)
    
    approver_ids = fields.One2many(
        'approval.approver',
        'hr_attendance_explanation_id',
        string="Thông tin phê duyệt"
    )
    
    condition_visible_button_refuse_approve = fields.Boolean(
        compute='_compute_condition_visible_button_refuse_approve',
        string='Điều kiện hiện button duyệt và từ chối'
    )
    
    reason_for_refuse = fields.Text(
        string='Lý do từ chối',
        readonly=True,
        tracking=True
    )
    
    check_need_approve = fields.Boolean(
        string='Cần phê duyệt',
        compute='_compute_check_need_approve',
        search='_search_check_need_approve'
    )
    
    # === TIMESHEET INTEGRATION (Requires 'account' module) ===
    # TODO: Enable when account module is installed
    # ts_ids = fields.One2many(
    #     'account.analytic.line',
    #     'explanation_id',
    #     string='Timesheets'
    # )
    # 
    # show_action_view_timesheet = fields.Boolean(
    #     compute='_compute_show_action_view_timesheet'
    # )
    
    # === COMPUTED FIELDS ===
    @api.depends('employee_id', 'explanation_date')
    def _compute_name(self):
        """Auto-generate name from employee and date"""
        for rec in self:
            if rec.employee_id and rec.explanation_date:
                date_str = rec.explanation_date.strftime("%d/%m/%Y")
                rec.name = f'{rec.employee_id.name} giải trình công ngày {date_str}'
            else:
                rec.name = _('Giải trình chấm công')
    
    @api.depends('approver_ids.status')
    def _compute_condition_visible_button_refuse_approve(self):
        """Check if current user can approve/refuse"""
        for rec in self:
            pending_approvers = rec.approver_ids.filtered(
                lambda a: a.status == 'pending'
            ).sorted(key=lambda x: x.sequence)
            first_pending = pending_approvers[:1]
            rec.condition_visible_button_refuse_approve = (
                first_pending.user_id == self.env.user if first_pending else False
            )
    
    @api.depends('approver_ids', 'state', 'approver_ids.status', 'approver_ids.user_id')
    def _compute_check_need_approve(self):
        """Check if record needs approval from current user"""
        for rec in self:
            rec.check_need_approve = (
                rec.state == 'to_approve' and
                bool(rec.approver_ids.filtered(
                    lambda x: x.status == 'pending' and x.user_id == self.env.user
                ))
            )
    
    @api.model
    def _search_check_need_approve(self, operator, operand):
        """Search for records needing approval from current user"""
        if operator not in ['=', '!=']:
            raise UserError(_('Invalid domain operator %s') % operator)
        
        matching_approvers = self.env['approval.approver'].search([
            ('status', '=', 'pending'),
            ('user_id', '=', self.env.user.id),
            ('hr_attendance_explanation_id', '!=', False),
            ('hr_attendance_explanation_id.state', '=', 'to_approve')
        ])
        matching_ids = matching_approvers.mapped('hr_attendance_explanation_id').ids
        
        if (operator == '=' and operand) or (operator == '!=' and not operand):
            return [('id', 'in', matching_ids)]
        else:
            return [('id', 'not in', matching_ids)]
    
    # @api.depends('ts_ids', 'state', 'submission_code')
    # def _compute_show_action_view_timesheet(self):
    #     """Show timesheet action button if applicable - requires account module"""
    #     for rec in self:
    #         rec.show_action_view_timesheet = (
    #             bool(rec.ts_ids) and
    #             rec.submission_code in ['TSDA', 'TSNDA']
    #         )
    
    # === CONSTRAINTS ===
    @api.constrains('explanation_date')
    def _check_explanation_date(self):
        """Prevent creating explanation for future dates"""
        for rec in self:
            if rec.explanation_date and rec.explanation_date > fields.Date.context_today(self):
                raise ValidationError(_('Không thể tạo giải trình trong tương lai!'))
    
    @api.constrains('line_ids')
    def _check_line_ids(self):
        """Validate detail lines for MA (Missing Attendance) type"""
        for rec in self:
            if rec.submission_code == 'MA' and rec.state != 'new':
                check_in = rec.line_ids.filtered(lambda x: x.type == 'check_in')
                check_out = rec.line_ids.filtered(lambda x: x.type == 'check_out')
                if not check_in or not check_out:
                    raise ValidationError(_(
                        'Giải trình thiếu chấm công cần có cả giá trị Check In và Check Out'
                    ))
    
    # === CRUD OVERRIDES ===
    @api.model
    def fields_get(self, allfields=None, attributes=None):
        """Make fields readonly based on state"""
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
    
    # === ACTIONS ===
    def send_approve(self):
        """Send for approval"""
        self.ensure_one()
        
        # Check permissions
        if self.create_uid != self.env.user:
            raise UserError(_('Chỉ người tạo giải trình mới có thể gửi phê duyệt!'))
        
        # Validate date
        if self.explanation_date > fields.Date.context_today(self):
            raise UserError(_('Không thể tạo giải trình trong tương lai!'))
        
        # # Check for timesheet explanation types (requires account module)
        # if self.submission_code in ['TSDA', 'TSNDA']:
        #     if not self.ts_ids:
        #         return {
        #             'type': 'ir.actions.act_window',
        #             'name': _('Tạo timesheet giải trình'),
        #             'res_model': 'explanation.task.timesheet',
        #             'view_mode': 'form',
        #             'context': {
        #                 'default_explanation_id': self.id,
        #                 'default_type': self.submission_code,
        #             },
        #             'target': 'new',
        #         }
        
        if self.submission_code not in ['TSDA', 'TSNDA']:
            # Validate detail lines
            if not self.line_ids:
                raise ValidationError(_('Bạn cần chọn giá trị điều chỉnh mới!'))
            
            # Check max attendance request time
            date_check_out = False
            if self.submission_type_id.code != 'MA':
                date_check_out = self.hr_attendance_id.check_out
            else:
                time_check_out_line = self.line_ids.filtered(lambda x: x.type == 'check_out')
                if time_check_out_line and self.explanation_date:
                    date_check_out = self.explanation_date + self._float_to_relativedelta(
                        time_check_out_line.time
                    ) - relativedelta(hours=7)
            
            # Check time limit
            en_max_attendance_request = float(
                self.env['ir.config_parameter'].sudo().get_param(
                    'en_max_attendance_request', default=0
                )
            )
            time_now = datetime.now()
            if (en_max_attendance_request >= 0 and date_check_out and 
                date_check_out + relativedelta(hours=en_max_attendance_request) <= time_now):
                raise UserError(_('Đã quá thời gian cho phép giải trình'))
        
        # Apply approvers and send notification
        self.apply_approver()
    
    def apply_approver(self):
        """Create approval flow and notify first approver"""
        self._compute_approver_ids()
        
        # Get first pending approver
        first_approver = self.approver_ids.filtered(
            lambda a: a.status == 'new'
        ).sorted(key=lambda a: a.sequence)[:1]
        
        if first_approver:
            self._send_notify(
                'Bạn có bản ghi Giải trình cần phê duyệt. Bấm tại đây để xem chi tiết.',
                first_approver.user_id
            )
        
        # Update approvers to pending
        self.approver_ids.filtered(lambda a: a.status == 'new').write({
            'status': 'pending'
        })
        
        # Update state
        self.write({'state': 'to_approve'})
    
    def _compute_approver_ids(self):
        """Compute approval flow based on rules"""
        self.ensure_one()
        
        # TODO: Implement approval flow logic based on office.approve.flow
        # For now, use simple manager approval
        manager = self.employee_id.parent_id.user_id
        if not manager:
            raise UserError(_('Không tìm thấy người phê duyệt. Vui lòng kiểm tra cấu trúc tổ chức.'))
        
        approver_vals = [(5, 0, 0)]  # Clear existing
        approver_vals.append(Command.create({
            'user_id': manager.id,
            'status': 'new',
            'sequence': 1,
        }))
        
        self.update({'approver_ids': approver_vals})
    
    def button_approve(self):
        """Approve explanation"""
        for rec in self.sudo():
            # Check permissions
            if not rec.condition_visible_button_refuse_approve:
                raise UserError(_('Bạn không được phép duyệt bản ghi này'))
            
            # Update current approver
            approver = rec.approver_ids.filtered(
                lambda a: a.user_id == self.env.user
            )
            approver.write({'status': 'approved'})
            
            # Check if all approved
            if all(a.status == 'approved' for a in rec.approver_ids):
                rec.write({'state': 'approved'})
                rec._apply_attendance_changes()
                rec._send_notify(
                    'Bản ghi Giải trình của bạn đã được phê duyệt.',
                    rec.employee_id.user_id
                )
            else:
                # Notify next approver
                next_approver = rec.approver_ids.filtered(
                    lambda a: a.status == 'pending'
                ).sorted(key=lambda a: a.sequence)[:1]
                if next_approver:
                    rec._send_notify(
                        'Bạn có bản ghi Giải trình cần phê duyệt.',
                        next_approver.user_id
                    )
    
    def button_refuse(self):
        """Open wizard to refuse explanation"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Lý do từ chối'),
            'res_model': 'reason.for.refuse.wizard',
            'view_mode': 'form',
            'context': {'default_hr_attendance_explanation_id': self.id},
            'target': 'new',
        }
    
    def button_cancel(self):
        """Cancel explanation"""
        self.write({'state': 'cancel'})
    
    def _apply_attendance_changes(self):
        """Apply approved changes to attendance record"""
        self.ensure_one()
        
        # if self.submission_code in ['TSDA', 'TSNDA']:
        #     # Handle timesheet explanations (requires account module)
        #     self.ts_ids.with_context(timesheet_from_explanation=True).sudo().write({
        #         'en_state': 'approved'
        #     })
        
        if self.submission_code not in ['TSDA', 'TSNDA']:
            # Handle attendance time adjustments
            attendance_vals = {'en_missing_attendance': False}
            
            for line in self.line_ids:
                convert_date = (self.explanation_date +
                              self._float_to_relativedelta(line.time) -
                              relativedelta(hours=7))
                attendance_vals[line.type] = convert_date
            
            if self.submission_type_id.code == 'MA':
                # Create missing attendance
                attendance_vals.update({
                    'employee_id': self.employee_id.id,
                    'en_location_id': self.employee_id.work_location_id.id,
                    'en_location_checkout_id': self.employee_id.work_location_id.id,
                })
                
                if not self.missing_hr_attendance_id:
                    self.missing_hr_attendance_id = self.env['hr.attendance'].with_user(
                        self.employee_id.user_id or self.env.user
                    ).create(attendance_vals)
                else:
                    self.missing_hr_attendance_id.sudo().write(attendance_vals)
                
                hr_attendance = self.missing_hr_attendance_id
            else:
                # Update existing attendance
                self.hr_attendance_id.sudo().write(attendance_vals)
                hr_attendance = self.hr_attendance_id
            
            # Recompute worked hours
            hr_attendance._compute_worked_hours()
    
    def _float_to_relativedelta(self, float_hour):
        """Convert float hour to relativedelta"""
        if float_hour >= 24:
            float_hour = 23.9999
        minute = (float_hour % 1) * 60
        second = (minute % 1) * 60
        return relativedelta(
            hour=int(float_hour),
            minute=int(minute),
            second=int(second),
            microsecond=0
        )
    
    def _send_notify(self, message, user):
        """Send notification to user"""
        if not user:
            return
        
        self.message_post(
            body=message,
            partner_ids=user.partner_id.ids,
            message_type='notification',
            subtype_xmlid='mail.mt_comment',
        )
    
    # def action_view_timesheet(self):
    #     """View related timesheets - requires account module"""
    #     if not self.ts_ids:
    #         return
    #     
    #     return {
    #         'name': _('Timesheets'),
    #         'type': 'ir.actions.act_window',
    #         'res_model': 'account.analytic.line',
    #         'view_mode': 'tree,form',
    #         'domain': [('id', 'in', self.ts_ids.ids)],
    #         'context': {'default_explanation_id': self.id},
    #     }
