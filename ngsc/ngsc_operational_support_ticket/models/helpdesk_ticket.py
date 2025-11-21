from odoo import models, fields, api, _


class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    operational_ticket_id = fields.Many2one('operational.support.ticket', string='Operational Ticket',
                                            ondelete='set null', readonly=True, index=True, copy=False, unique=True)
    en_type_request_id = fields.Many2one(required=False)
    en_system_id = fields.Many2one(required=False)
    en_subsystem_id = fields.Many2one( required=False)
    workpackage_id = fields.Many2one(required=False)
    en_stage_type_id = fields.Many2one(required=False)
    handler_id = fields.Many2many(required=False)
    ticket_type_id = fields.Many2one(required=False)
    resource_id = fields.Many2one(required=False)
    urgency_id = fields.Many2one(required=False)
    infulence_id = fields.Many2one(required=False)
    supervisor_id = fields.Many2one(required=False)
    project_id = fields.Many2one(required=False)

    def write(self, values):
        res = super(HelpdeskTicket, self).write(values)
        for rec in self:
            if 'stage_id' in values:
                if rec.stage_id.en_state == 'received':
                    rec.operational_ticket_id.en_state = 'received'
                if rec.stage_id.en_state == 'compelete' or rec.stage_id.en_state == 'close':
                    rec.operational_ticket_id.en_state = 'completed'
                if rec.stage_id.en_state == 'doing':
                    rec.operational_ticket_id.en_state = 'doing'
                if rec.stage_id.en_state == 'wait':
                    rec.operational_ticket_id.en_state = 'wait'
                if rec.stage_id.en_state == 'wait':
                    rec.operational_ticket_id.en_state = 'wait'
                if rec.stage_id.en_state == 'cancel':
                    rec.operational_ticket_id.en_state = 'cancel'
            if 'user_request_id' in values:
                rec.operational_ticket_id.user_request_id = rec.user_request_id.id
            if 'date_log' in values:
                rec.operational_ticket_id.date_log = rec.date_log
            if 'supervisor_id' in values:
                rec.operational_ticket_id.supervisor_id = rec.supervisor_id.id
            if 'text_description' in values:
                rec.operational_ticket_id.text_description = rec.text_description
            if 'text_reason' in values:
                rec.operational_ticket_id.text_reason = rec.text_reason
        return res

