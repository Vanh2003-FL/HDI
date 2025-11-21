from odoo import models, fields, api, _, exceptions
from odoo.exceptions import ValidationError, UserError, AccessError


class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    en_stage_type_id = fields.Many2one(required=False)
    workpackage_id = fields.Many2one( required=False)

    project_stage_id = fields.Many2one("project.task", string="Giai đoạn dự án")
    project_package_id = fields.Many2one("project.task", string="Gói việc")

class OperationalSupportTicket(models.Model):
    _inherit = "operational.support.ticket"

    def _get_default_values(self):
        system = self.env['en.system'].sudo().search([('name', '=', 'Odoo')], order='id desc', limit=1)
        resource = self.env['helpdesk.source'].sudo().search([('name', '=', 'Website hỗ trợ')], order='id desc',
                                                             limit=1)
        project = self.env['project.project'].sudo().search(
            [('en_code', '=', 'NGSC_UDNB')], order='id desc', limit=1)
        project_stage_id, project_package_id = False, False
        project_stage = project.en_current_version.wbs_task_ids.filtered(lambda x: x.category == "phase" and x.name == "Triển khai")
        if project_stage:
            project_stage_id = project_stage[0].id
            project_package_id = project_stage[0].child_ids.filtered(lambda x: x.category == "package" and x.name == "Hỗ trợ vận hành hệ thống").id
        return {
            'name': self.name,
            'en_code': self.en_code,
            'user_request_id': self.user_request_id.id,
            'date_log': self.date_log,
            'supervisor_id': self.supervisor_id.id,
            'text_description': self.text_description,
            'text_reason': self.text_reason,
            'project_id': project.id,
            'en_system_id': system.id,
            'resource_id': resource.id,
            'project_stage_id': project_stage_id,
            'project_package_id': project_package_id,
        }