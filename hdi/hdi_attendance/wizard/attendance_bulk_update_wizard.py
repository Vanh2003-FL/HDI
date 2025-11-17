# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AttendanceBulkUpdateWizard(models.TransientModel):
    _name = 'attendance.bulk.update.wizard'
    _description = 'Wizard cập nhật hàng loạt chấm công'

    attendance_ids = fields.Many2many(
        'hr.attendance',
        string='Chấm công',
        required=True
    )
    
    update_type = fields.Selection([
        ('work_location', 'Cập nhật địa điểm'),
        ('work_shift', 'Cập nhật ca làm việc'),
        ('approve_explanation', 'Duyệt giải trình'),
        ('reject_explanation', 'Từ chối giải trình'),
    ], string='Loại cập nhật', required=True)
    
    work_location_id = fields.Many2one(
        'hr.work.location',
        string='Địa điểm làm việc mới'
    )
    
    work_shift = fields.Selection([
        ('morning', 'Ca sáng'),
        ('afternoon', 'Ca chiều'),
        ('night', 'Ca tối'),
        ('full', 'Ca ngày'),
        ('flexible', 'Ca linh hoạt'),
    ], string='Ca làm việc mới')
    
    note = fields.Text(
        string='Ghi chú',
        help='Ghi chú về việc cập nhật hàng loạt'
    )

    def action_update(self):
        """Thực hiện cập nhật hàng loạt"""
        self.ensure_one()
        
        if not self.attendance_ids:
            raise UserError(_('Vui lòng chọn ít nhất một bản ghi chấm công!'))
        
        if self.update_type == 'work_location':
            if not self.work_location_id:
                raise UserError(_('Vui lòng chọn địa điểm làm việc!'))
            self.attendance_ids.write({
                'hdi_work_location_id': self.work_location_id.id
            })
            message = _('Đã cập nhật địa điểm làm việc cho %d bản ghi') % len(self.attendance_ids)
            
        elif self.update_type == 'work_shift':
            if not self.work_shift:
                raise UserError(_('Vui lòng chọn ca làm việc!'))
            self.attendance_ids.write({
                'hdi_work_shift': self.work_shift
            })
            message = _('Đã cập nhật ca làm việc cho %d bản ghi') % len(self.attendance_ids)
            
        elif self.update_type == 'approve_explanation':
            for attendance in self.attendance_ids:
                for explanation in attendance.hdi_explanation_ids.filtered(lambda e: e.state == 'pending'):
                    explanation.action_approve()
            message = _('Đã duyệt giải trình cho các bản ghi được chọn')
            
        elif self.update_type == 'reject_explanation':
            for attendance in self.attendance_ids:
                for explanation in attendance.hdi_explanation_ids.filtered(lambda e: e.state == 'pending'):
                    explanation.action_reject()
            message = _('Đã từ chối giải trình cho các bản ghi được chọn')
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Cập nhật thành công!'),
                'message': message,
                'type': 'success',
                'sticky': False,
            }
        }