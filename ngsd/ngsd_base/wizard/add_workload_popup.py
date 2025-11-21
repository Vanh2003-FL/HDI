from odoo import models, api, fields, _, exceptions

from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)


class AddWorkloadPopup(models.TransientModel):
    _name = 'add.workload.popup'
    _description = 'YC tăng wl'

    detail_id = fields.Many2one('en.lender.employee.detail', string='Detail ID')
    add_workload = fields.Float(string='Workload yêu cầu')
    workload = fields.Float(string='Workload hiện tại', related='detail_id.workload')
    type = fields.Char()

    def button_confirm(self):
        lender_id = self.detail_id.lender_employee_id
        if self.type == 'request':
            if self.add_workload > self.detail_id.workload:
                lender_id.send_notify('Bạn có một yêu cầu tăng WL cho mượn', lender_id.lender_id.user_id)
                lender_id.message_post(body=f'{lender_id.borrower_id.display_name} yêu cầu tăng WL cho dòng {self.detail_id.id}: {self.workload} > {self.add_workload}')
                self.detail_id.write({
                    'add_workload': self.add_workload,
                })

            else:
                raise UserError('Workload mới phải lớn hơn Workload hiện tại')
        elif self.type == 'confirm':
            lender_id.send_notify(f'{lender_id.lender_id.display_name} Đã đồng ý yêu cầu tăng WL đi mượn của bạn)', lender_id.borrower_id)
            lender_id.message_post(body=f'{lender_id.lender_id.display_name} duyệt tăng WL cho dòng {self.detail_id.id}: {self.workload} > {self.add_workload}')
            self.detail_id.write({
                'workload': self.add_workload,
                'add_workload': False,
            })
            self.env['en.department.resource'].search([('lender_employee_detail_id', '=', self.detail_id.id)]).write({
                'workload': self.add_workload
            })

    def button_cancel(self):
        lender_id = self.detail_id.lender_employee_id
        lender_id.send_notify(f'{lender_id.lender_id.display_name} Đã từ chối yêu cầu tăng WL đi mượn của bạn)', lender_id.borrower_id)
        lender_id.message_post(body=f'{lender_id.lender_id.display_name} từ chối yêu cầu tăng WL cho dòng {self.detail_id.id}: {self.workload} > {self.add_workload}')
        self.detail_id.write({
            'add_workload': False,
        })
