
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from datetime import date

class TimesheetCheckoutLine(models.TransientModel):
    """wizard_id = fields.Many2one('timesheet.checkout.wizard', string='Wizard', ondelete='cascade', invisible=True)
    Mỗi dòng trong bảng khai báo công việc (task + mô tả + số giờ làm).
    Chỉ là dữ liệu tạm, chưa ghi vào bảng chính.
    """
    _name = 'timesheet.checkout.line'
    _description = 'Dòng timesheet tạm (chỉ để hiển thị trong wizard)'

    wizard_id = fields.Many2one('timesheet.checkout.wizard', string='Wizard', ondelete='cascade')
    task_id = fields.Many2one('project.task', string='Công việc')
    description = fields.Text(string='Mô tả công việc')
    hours = fields.Float(string='Giờ làm', required=True)
    is_overtime = fields.Boolean(string='Là tăng ca?')

    def action_open_detail(self):
        """
        Mở popup phụ để nhập chi tiết cho dòng hiện tại.
        """
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'timesheet.checkout.line.wizard',
            'view_mode': 'form',
            'view_id': self.env.ref('ngsc_timesheet_checkout.view_timesheet_checkout_line_wizard_form').id,
            'target': 'new',
            'context': {
                'default_task_id': self.task_id.id,
                'default_description': self.description,
                'default_hours': self.hours,
                'default_is_overtime': self.is_overtime,
                'parent_line_id': self.id,
            }
        }
