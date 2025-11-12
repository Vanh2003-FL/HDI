from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError, AccessError


class OperationalSupportTicket(models.Model):
    _name = 'operational.support.ticket'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Operational Support Ticket'
    _order = 'id desc'

    name = fields.Char(string='Tên ticket', required=True, index=True, tracking=True, copy=False)
    en_code = fields.Char('Mã ticket', copy=False)
    user_request_id = fields.Many2one('res.users', 'Người yêu cầu', default=lambda self: self.env.uid, tracking=True)
    date_log = fields.Datetime(string='Ngày log ticket', default=lambda self: fields.Datetime.now(),
                               required=True, tracking=True)
    supervisor_id = fields.Many2one('res.users', string='Người chịu trách nhiệm', tracking=True,  copy=False)
    text_description = fields.Html('Mô tả', required=True, tracking=True, copy=False)
    text_reason = fields.Html('Nguyên nhân', tracking=True, copy=False)
    en_state = fields.Selection(selection=[('draft', 'Mới'),
                                           ('sent', 'Đã gửi'),
                                           ('received', 'Đã tiếp nhận'),
                                           ('wait', 'Chờ xử lý'),
                                           ('doing', 'Đang xử lý'),
                                           ('completed', 'Hoàn thành'),
                                           ('cancel', 'Từ chối')],
                                string='Trạng thái ticket', default='draft', tracking=True, copy=False)
    helpdesk_ticket_id = fields.Many2one('helpdesk.ticket', string='Ticket Helpdesk', ondelete='set null',
                                         index=True, copy=False, unique=True, tracking=True)

    def name_get(self):
        result = []
        for ticket in self:
            result.append((ticket.id, "%s (#%d)" % (ticket.name, ticket._origin.id)))
        return result

    @api.model
    def create(self, vals):
        if not vals.get('en_code'):
            vals['en_code'] = self.env['ir.sequence'].next_by_code('code.helpdesk.ticket')
        return super().create(vals)

    def _get_default_values(self):
        system = self.env['en.system'].sudo().search([('name', '=', 'Odoo')], order='id desc', limit=1)
        resource = self.env['helpdesk.source'].sudo().search([('name', '=', 'Website hỗ trợ')], order='id desc',
                                                             limit=1)
        project = self.env['project.project'].sudo().search(
            [('en_code', '=', 'NGSC_UDNB')], order='id desc', limit=1)
        work_package = self.env['en.workpackage']
        project_stage = project.en_current_version.project_stage_ids.filtered(lambda s: s.stage_code == 'P.3')
        if project_stage:
            work_package = project_stage[0].order_line.filtered(lambda s: s.wp_code == 'W.6')
        return {
            'name': self.name,
            'en_code': self.en_code,
            'user_request_id': self.user_request_id.id,
            'date_log': self.date_log,
            'supervisor_id': self.supervisor_id.id,
            'text_description': self.text_description,
            'text_reason': self.text_reason,
            'project_id': project.id,
            'en_stage_type_id': project_stage.id,
            'workpackage_id': work_package.id,
            'en_system_id': system.id,
            'resource_id': resource.id,
        }

    def action_send_request(self):
        for rec in self.filtered(lambda x: x.en_state == 'draft'):
            values = rec._get_default_values()
            ticket = self.env['helpdesk.ticket'].create(values)
            rec.en_state = 'sent'
            rec.helpdesk_ticket_id = ticket.id
            ticket.operational_ticket_id = rec.id

    def unlink(self):
        if any(rec.en_state != 'draft' for rec in self):
            raise ValidationError('Chỉ được xóa ticket ở trạng thái "Mới".')
        return super().unlink()
