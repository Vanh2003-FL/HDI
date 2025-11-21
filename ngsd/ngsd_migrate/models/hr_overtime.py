from odoo import models, fields, api, _


class HrOvertime(models.Model):
    _inherit = 'en.hr.overtime'

    time = fields.Float(compute=False, readonly=False)
    state = fields.Selection(readonly=False)
    en_overtime_plan_id = fields.Many2one(required=False)

    def _constrains_count_overtime(self):
        return

    def _constrains_overlap_overtime(self):
        return

    import_map = fields.Char()

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if values.get('import_map') and not values.get('task_id'):
                package_id, name = values.get('import_map').split('--')
                values['task_id'] = self.env['project.task'].search([('en_task_position', '=', self.env.ref(package_id).id), ('name', '=', name)], limit=1).id
        return super(HrOvertime, self).create(vals_list)


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    en_state = fields.Selection(readonly=False)
    import_map = fields.Char()

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if values.get('import_map') and not values.get('task_id'):
                package_id, name = values.get('import_map').split('--')
                values['task_id'] = self.env['project.task'].search([('en_task_position', '=', self.env.ref(package_id).id), ('name', '=', name)], limit=1).id
            if values.get('task_id') and not values.get('account_id'):
                values['account_id'] = self.env['project.task'].browse(values.get('task_id')).project_id.analytic_account_id.id
        return super(AccountAnalyticLine, self).create(vals_list)
