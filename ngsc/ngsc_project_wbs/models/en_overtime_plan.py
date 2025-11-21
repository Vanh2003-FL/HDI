from odoo import models, fields, api, _


class OvertimePlan(models.Model):
    _inherit = "en.overtime.plan"

    @api.depends_context('uid')
    @api.depends('create_uid')
    def _search_project_of_create(self):
        uid = self.env.user.id
        for rec in self:
            _domain = [('task_ids.en_handler', '=', rec.create_uid.id or uid),
                       ('task_ids.project_wbs_state', '=', 'approved')]
            rec.en_project_ids = self.env['project.project'].search(_domain).ids

    @api.depends_context('uid')
    @api.depends('create_uid', 'en_project_id')
    def _get_en_work_domain(self):
        uid = self.env.user.id
        for rec in self:
            rec.en_work_domain = False
            if not rec.en_project_id:
                continue
            _domain = [('category', '=', 'task'),
                       ('en_handler', '=', rec.create_uid.id or uid),
                       ('project_id', '=', rec.en_project_id.id),
                       ('stage_id.en_mark', 'in', ['a', 'c', 'f']),
                       ('project_wbs_state', '=', 'approved')]
            rec.en_work_domain = self.env['project.task'].search(_domain).ids
