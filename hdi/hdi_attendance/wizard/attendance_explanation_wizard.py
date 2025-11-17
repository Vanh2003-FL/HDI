# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AttendanceExplanationWizard(models.TransientModel):
    _name = 'attendance.explanation.wizard'
    _description = 'Wizard giải trình chấm công'

    attendance_id = fields.Many2one(
        'hr.attendance',
        string='Chấm công',
        required=True
    )
    
    employee_id = fields.Many2one(
        'hr.employee',
        string='Nhân viên',
        related='attendance_id.employee_id',
        readonly=True
    )
    
    explanation_type = fields.Selection([
        ('late_checkin', 'Đi muộn'),
        ('early_checkout', 'Về sớm'),
        ('missing_checkout', 'Thiếu check-out'),
        ('location_issue', 'Vấn đề về địa điểm'),
        ('technical_issue', 'Sự cố kỹ thuật'),
        ('personal_emergency', 'Việc cá nhân khẩn cấp'),
        ('traffic_jam', 'Tắc đường'),
        ('public_transport', 'Phương tiện công cộng'),
        ('health_issue', 'Vấn đề sức khỏe'),
        ('family_emergency', 'Việc gia đình khẩn cấp'),
        ('other', 'Khác'),
    ], string='Loại giải trình', required=True)
    
    explanation = fields.Text(
        string='Giải trình chi tiết',
        required=True,
        help='Vui lòng mô tả chi tiết lý do và tình huống'
    )
    
    # Supporting information
    start_time_explanation = fields.Char(
        string='Giải thích về thời gian bắt đầu',
        help='Nếu có điều chỉnh thời gian check-in'
    )
    
    end_time_explanation = fields.Char(
        string='Giải thích về thời gian kết thúc',
        help='Nếu có điều chỉnh thời gian check-out'
    )
    
    proposed_checkin = fields.Datetime(
        string='Thời gian check-in đề xuất',
        help='Thời gian check-in thực tế mà bạn muốn điều chỉnh'
    )
    
    proposed_checkout = fields.Datetime(
        string='Thời gian check-out đề xuất',
        help='Thời gian check-out thực tế mà bạn muốn điều chỉnh'
    )
    
    # Supporting documents
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'explanation_wizard_attachment_rel',
        'wizard_id',
        'attachment_id',
        string='Tài liệu đính kèm',
        help='Đính kèm các tài liệu chứng minh (giấy tờ y tế, ảnh chụp tình huống...)'
    )
    
    # Manager notification
    notify_manager = fields.Boolean(
        string='Thông báo cho quản lý',
        default=True,
        help='Gửi thông báo email cho quản lý trực tiếp'
    )
    
    manager_id = fields.Many2one(
        'hr.employee',
        string='Quản lý',
        related='employee_id.parent_id',
        readonly=True
    )
    
    # Current attendance info (readonly)
    current_checkin = fields.Datetime(
        string='Check-in hiện tại',
        related='attendance_id.check_in',
        readonly=True
    )
    
    current_checkout = fields.Datetime(
        string='Check-out hiện tại',
        related='attendance_id.check_out',
        readonly=True
    )
    
    attendance_issues = fields.Text(
        string='Các vấn đề phát hiện',
        compute='_compute_attendance_issues',
        readonly=True
    )

    @api.depends('attendance_id')
    def _compute_attendance_issues(self):
        """Hiển thị các vấn đề của chấm công"""
        for wizard in self:
            issues = []
            attendance = wizard.attendance_id
            
            if attendance.hdi_is_late:
                issues.append(f"• Đi muộn {attendance.hdi_late_minutes:.0f} phút")
            if attendance.hdi_is_early_leave:
                issues.append(f"• Về sớm {attendance.hdi_early_leave_minutes:.0f} phút")
            if attendance.hdi_is_missing_checkout:
                issues.append("• Thiếu check-out")
            if attendance.check_in_distance > 100:
                issues.append(f"• Check-in xa địa điểm làm việc ({attendance.check_in_distance:.0f}m)")
            if attendance.check_out_distance > 500:
                issues.append(f"• Check-out xa địa điểm làm việc ({attendance.check_out_distance:.0f}m)")
            
            wizard.attendance_issues = '\n'.join(issues) if issues else 'Không phát hiện vấn đề'

    @api.onchange('explanation_type')
    def _onchange_explanation_type(self):
        """Tự động điền template giải trình"""
        if self.explanation_type:
            templates = {
                'late_checkin': 'Tôi đi muộn do: ',
                'early_checkout': 'Tôi về sớm do: ',
                'missing_checkout': 'Tôi quên check-out do: ',
                'location_issue': 'Tôi không thể check-in/out đúng địa điểm do: ',
                'technical_issue': 'Có sự cố kỹ thuật: ',
                'personal_emergency': 'Có việc cá nhân khẩn cấp: ',
                'traffic_jam': 'Bị tắc đường trên đường: ',
                'public_transport': 'Phương tiện công cộng gặp sự cố: ',
                'health_issue': 'Có vấn đề sức khỏe: ',
                'family_emergency': 'Có việc gia đình khẩn cấp: ',
                'other': 'Lý do khác: ',
            }
            self.explanation = templates.get(self.explanation_type, '')

    def action_submit_explanation(self):
        """Gửi giải trình"""
        self.ensure_one()
        
        # Validate
        if not self.explanation:
            raise UserError(_('Vui lòng nhập giải trình chi tiết!'))
        
        # Create explanation record
        explanation_vals = {
            'attendance_id': self.attendance_id.id,
            'explanation': self.explanation,
            'supporting_documents': [(6, 0, self.attachment_ids.ids)],
        }
        
        explanation = self.env['attendance.explanation'].create(explanation_vals)
        
        # Create exception record for tracking
        exception_types = {
            'late_checkin': 'late_checkin',
            'early_checkout': 'early_checkout', 
            'missing_checkout': 'missing_checkout',
            'location_issue': 'location_violation',
            'technical_issue': 'other',
            'personal_emergency': 'other',
            'traffic_jam': 'other',
            'public_transport': 'other',
            'health_issue': 'other',
            'family_emergency': 'other',
            'other': 'other',
        }
        
        exception_type = exception_types.get(self.explanation_type, 'other')
        
        exception = self.env['attendance.exception'].create({
            'name': f"Giải trình: {dict(self._fields['explanation_type'].selection)[self.explanation_type]}",
            'employee_id': self.employee_id.id,
            'attendance_id': self.attendance_id.id,
            'exception_type': exception_type,
            'exception_date': self.attendance_id.check_in_date,
            'description': self.explanation,
            'reason': f"Loại: {dict(self._fields['explanation_type'].selection)[self.explanation_type]}",
            'state': 'submitted',
            'submitted_by': self.env.user.id,
            'submitted_date': fields.Datetime.now(),
        })
        
        # Apply proposed time adjustments if any
        if self.proposed_checkin or self.proposed_checkout:
            attendance_vals = {}
            if self.proposed_checkin:
                attendance_vals['check_in'] = self.proposed_checkin
            if self.proposed_checkout:
                attendance_vals['check_out'] = self.proposed_checkout
            
            if attendance_vals:
                self.attendance_id.write(attendance_vals)
                exception.resolution = f"Đã điều chỉnh thời gian: {attendance_vals}"
        
        # Send notification to manager
        if self.notify_manager and self.manager_id and self.manager_id.user_id:
            self._send_manager_notification(explanation, exception)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Giải trình đã được gửi!'),
                'message': _('Giải trình của bạn đã được gửi và đang chờ phê duyệt từ quản lý.'),
                'type': 'success',
                'sticky': False,
            }
        }

    def _send_manager_notification(self, explanation, exception):
        """Gửi thông báo cho quản lý"""
        manager_partner = self.manager_id.user_id.partner_id
        
        # Create mail message
        body = _("""
        <p>Kính gửi Anh/Chị,</p>
        <p>Nhân viên <strong>%(employee_name)s</strong> đã gửi giải trình chấm công cần phê duyệt.</p>
        
        <p><strong>Chi tiết:</strong></p>
        <ul>
            <li>Ngày: %(date)s</li>
            <li>Loại giải trình: %(type)s</li>
            <li>Nội dung: %(explanation)s</li>
        </ul>
        
        <p>Vui lòng xem xét và phê duyệt giải trình này.</p>
        
        <p>Trân trọng,<br/>Hệ thống chấm công HDI</p>
        """) % {
            'employee_name': self.employee_id.name,
            'date': self.attendance_id.check_in_date,
            'type': dict(self._fields['explanation_type'].selection)[self.explanation_type],
            'explanation': self.explanation,
        }
        
        # Send notification
        exception.message_notify(
            partner_ids=[manager_partner.id],
            subject=_('Giải trình chấm công cần phê duyệt - %s') % self.employee_id.name,
            body=body,
            record_name=exception.display_name,
        )

    def action_cancel(self):
        """Hủy wizard"""
        return {'type': 'ir.actions.act_window_close'}