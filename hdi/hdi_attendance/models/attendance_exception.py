# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AttendanceException(models.Model):
    _name = 'attendance.exception'
    _description = 'Ngoại lệ chấm công'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Tiêu đề',
        required=True,
        tracking=True
    )
    
    employee_id = fields.Many2one(
        'hr.employee',
        string='Nhân viên',
        required=True,
        tracking=True
    )
    
    attendance_id = fields.Many2one(
        'hr.attendance',
        string='Chấm công liên quan',
        tracking=True
    )
    
    exception_type = fields.Selection([
        ('missing_checkin', 'Thiếu check-in'),
        ('missing_checkout', 'Thiếu check-out'),
        ('late_checkin', 'Đi muộn'),
        ('early_checkout', 'Về sớm'),
        ('location_violation', 'Vi phạm địa điểm'),
        ('overtime_excess', 'Vượt giờ làm việc'),
        ('duplicate_attendance', 'Chấm công trùng lặp'),
        ('manual_adjustment', 'Điều chỉnh thủ công'),
        ('other', 'Khác'),
    ], string='Loại ngoại lệ', required=True, tracking=True)
    
    exception_date = fields.Date(
        string='Ngày',
        required=True,
        default=fields.Date.today,
        tracking=True
    )
    
    description = fields.Text(
        string='Mô tả chi tiết',
        required=True
    )
    
    reason = fields.Text(
        string='Lý do',
        help='Lý do gây ra ngoại lệ'
    )
    
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('submitted', 'Đã gửi'),
        ('approved', 'Đã duyệt'),
        ('rejected', 'Từ chối'),
        ('resolved', 'Đã giải quyết'),
    ], string='Trạng thái', default='draft', tracking=True)
    
    # Approval workflow
    submitted_by = fields.Many2one(
        'res.users',
        string='Người gửi',
        tracking=True
    )
    
    submitted_date = fields.Datetime(
        string='Ngày gửi',
        tracking=True
    )
    
    approved_by = fields.Many2one(
        'res.users',
        string='Người duyệt',
        tracking=True
    )
    
    approved_date = fields.Datetime(
        string='Ngày duyệt',
        tracking=True
    )
    
    manager_comment = fields.Text(
        string='Nhận xét của quản lý'
    )
    
    # Resolution
    resolution = fields.Text(
        string='Cách giải quyết'
    )
    
    resolved_by = fields.Many2one(
        'res.users',
        string='Người giải quyết',
        tracking=True
    )
    
    resolved_date = fields.Datetime(
        string='Ngày giải quyết',
        tracking=True
    )
    
    # Supporting documents
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'exception_attachment_rel',
        'exception_id',
        'attachment_id',
        string='Tài liệu đính kèm'
    )
    
    # Impact assessment
    impact_hours = fields.Float(
        string='Ảnh hưởng (giờ)',
        help='Số giờ bị ảnh hưởng bởi ngoại lệ'
    )
    
    financial_impact = fields.Monetary(
        string='Ảnh hưởng tài chính',
        currency_field='currency_id'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id
    )
    
    # Recurrence tracking
    is_recurring = fields.Boolean(
        string='Ngoại lệ lặp lại',
        help='Đánh dấu nếu đây là ngoại lệ hay xảy ra với nhân viên này'
    )
    
    occurrence_count = fields.Integer(
        string='Số lần xảy ra',
        compute='_compute_occurrence_count'
    )
    
    # Priority
    priority = fields.Selection([
        ('low', 'Thấp'),
        ('medium', 'Trung bình'),
        ('high', 'Cao'),
        ('urgent', 'Khẩn cấp'),
    ], string='Độ ưu tiên', default='medium', tracking=True)

    @api.depends('employee_id', 'exception_type')
    def _compute_occurrence_count(self):
        """Đếm số lần xảy ra ngoại lệ tương tự"""
        for rec in self:
            if rec.employee_id and rec.exception_type:
                count = self.search_count([
                    ('employee_id', '=', rec.employee_id.id),
                    ('exception_type', '=', rec.exception_type),
                    ('id', '!=', rec.id),
                ])
                rec.occurrence_count = count
                rec.is_recurring = count >= 2
            else:
                rec.occurrence_count = 0
                rec.is_recurring = False

    @api.onchange('exception_type')
    def _onchange_exception_type(self):
        """Auto-fill name based on exception type"""
        if self.exception_type:
            type_names = dict(self._fields['exception_type'].selection)
            self.name = type_names.get(self.exception_type, '')

    def action_submit(self):
        """Gửi ngoại lệ để phê duyệt"""
        self.ensure_one()
        if self.state != 'draft':
            raise ValidationError(_('Chỉ có thể gửi ngoại lệ ở trạng thái Nháp'))
        
        self.write({
            'state': 'submitted',
            'submitted_by': self.env.user.id,
            'submitted_date': fields.Datetime.now(),
        })
        
        # Send notification to manager
        self._send_notification_to_manager()
        
        return True

    def action_approve(self):
        """Phê duyệt ngoại lệ"""
        self.ensure_one()
        if self.state != 'submitted':
            raise ValidationError(_('Chỉ có thể duyệt ngoại lệ đã được gửi'))
        
        self.write({
            'state': 'approved',
            'approved_by': self.env.user.id,
            'approved_date': fields.Datetime.now(),
        })
        
        # Auto-resolve if possible
        self._auto_resolve()
        
        return True

    def action_reject(self):
        """Từ chối ngoại lệ"""
        self.ensure_one()
        if self.state != 'submitted':
            raise ValidationError(_('Chỉ có thể từ chối ngoại lệ đã được gửi'))
        
        self.write({
            'state': 'rejected',
            'approved_by': self.env.user.id,
            'approved_date': fields.Datetime.now(),
        })
        
        return True

    def action_resolve(self):
        """Giải quyết ngoại lệ"""
        self.ensure_one()
        if self.state not in ['approved']:
            raise ValidationError(_('Chỉ có thể giải quyết ngoại lệ đã được duyệt'))
        
        self.write({
            'state': 'resolved',
            'resolved_by': self.env.user.id,
            'resolved_date': fields.Datetime.now(),
        })
        
        return True

    def action_reset_to_draft(self):
        """Đưa về trạng thái nháp"""
        self.ensure_one()
        self.write({
            'state': 'draft',
            'submitted_by': False,
            'submitted_date': False,
            'approved_by': False,
            'approved_date': False,
        })
        return True

    def _send_notification_to_manager(self):
        """Gửi thông báo đến quản lý"""
        if not self.employee_id.parent_id:
            return
        
        partner = self.employee_id.parent_id.user_id.partner_id
        if not partner:
            return
        
        self.message_notify(
            partner_ids=[partner.id],
            subject=_('Ngoại lệ chấm công cần phê duyệt'),
            body=_('Nhân viên %s đã gửi ngoại lệ chấm công "%s" cần được phê duyệt.') % 
                 (self.employee_id.name, self.name),
            record_name=self.display_name,
        )

    def _auto_resolve(self):
        """Tự động giải quyết ngoại lệ nếu có thể"""
        if self.exception_type == 'missing_checkout' and self.attendance_id:
            # Auto checkout at end of shift
            expected_checkout = self.attendance_id.check_in + timedelta(hours=8)
            self.attendance_id.write({
                'check_out': expected_checkout,
            })
            self.resolution = _('Tự động check-out lúc %s') % expected_checkout.strftime('%H:%M:%S')
            self.action_resolve()

    @api.model
    def create_from_attendance(self, attendance, exception_type, description):
        """Tạo ngoại lệ từ chấm công"""
        exception = self.create({
            'name': f"{dict(self._fields['exception_type'].selection)[exception_type]} - {attendance.employee_id.name}",
            'employee_id': attendance.employee_id.id,
            'attendance_id': attendance.id,
            'exception_type': exception_type,
            'exception_date': attendance.check_in_date,
            'description': description,
            'state': 'submitted',
            'submitted_by': attendance.create_uid.id or self.env.user.id,
            'submitted_date': fields.Datetime.now(),
        })
        return exception


class AttendanceExplanation(models.Model):
    _name = 'attendance.explanation'
    _description = 'Giải trình chấm công'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    attendance_id = fields.Many2one(
        'hr.attendance',
        string='Chấm công',
        required=True,
        ondelete='cascade'
    )
    
    employee_id = fields.Many2one(
        'hr.employee',
        string='Nhân viên',
        related='attendance_id.employee_id',
        store=True
    )
    
    explanation = fields.Text(
        string='Giải trình',
        required=True
    )
    
    supporting_documents = fields.Many2many(
        'ir.attachment',
        string='Tài liệu hỗ trợ'
    )
    
    state = fields.Selection([
        ('pending', 'Chờ duyệt'),
        ('approved', 'Đã duyệt'),
        ('rejected', 'Từ chối'),
    ], string='Trạng thái', default='pending', tracking=True)
    
    manager_comment = fields.Text(
        string='Nhận xét của quản lý'
    )
    
    approved_by = fields.Many2one(
        'res.users',
        string='Người duyệt'
    )
    
    approved_date = fields.Datetime(
        string='Ngày duyệt'
    )

    def action_approve(self):
        """Duyệt giải trình"""
        self.write({
            'state': 'approved',
            'approved_by': self.env.user.id,
            'approved_date': fields.Datetime.now(),
        })

    def action_reject(self):
        """Từ chối giải trình"""
        self.write({
            'state': 'rejected',
            'approved_by': self.env.user.id,
            'approved_date': fields.Datetime.now(),
        })