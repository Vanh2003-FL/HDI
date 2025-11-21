from odoo import models, fields, api, _, exceptions
from odoo.exceptions import UserError
from datetime import datetime
from dateutil.relativedelta import relativedelta


class LeavePrọectPopup(models.TransientModel):
    _name = 'leave.project.popup'
    _description = 'LeaveProjectPopup'

    date = fields.Date('Ngày rời dự án', required=False)
    resource_project_id = fields.Many2one('resource.project')
    type = fields.Selection(selection=[('match', 'Rời đúng ngày'), ('soon', 'Rời sớm hơn dự kiến')], string='Loại rời dự án', default='soon', required=True)

    @api.onchange('type')
    def onchange_type(self):
        for rec in self:
            if rec.type != 'soon':
                rec.date = False

    @api.onchange('date')
    def onchange_date(self):
        for rec in self:
            if rec.date and rec.resource_project_id and (rec.date < rec.resource_project_id.date_start or rec.date > rec.resource_project_id.date_end + relativedelta(days=1)):
                raise UserError('Ngày rời phải nằm trong quãng thời gian của nhân sự trong dự án')

    def action_leave(self):
        if self.type == 'soon' and self.date:
            self.resource_project_id.action_leave(self.date)
        if self.type == 'match':
            self.resource_project_id.action_inactive(self.resource_project_id.date_end + relativedelta(days=1))
