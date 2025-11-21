from odoo import models, fields, api
import json
from lxml import etree


class ResourcePlanning(models.Model):
    _inherit = 'en.resource.planning'

    version_number = fields.Char(readonly=False)
    state = fields.Selection(readonly=False)

    def _constrains_overload(self):
        return

    def _constrains_no_more_than_one(self):
        return

    @api.depends('order_line.en_md_migrate', 'order_line.workload', 'order_line')
    def _compute_resource_total(self):
        for rec in self:
            rec.resource_total = sum(line.en_md_migrate * line.workload for line in rec.order_line)


class ResourceDetail(models.Model):
    _inherit = 'en.resource.detail'

    type_id = fields.Many2one(required=False)
    job_position_id = fields.Many2one(required=False)
    en_md_migrate = fields.Float()

    @api.model
    def create(self, vals):
        if not 'type_id' in vals and vals.get('employee_id'):
            vals['type_id'] = self.env['hr.employee'].browse(vals.get('employee_id')).en_type_id.id
        detail = super(ResourceDetail, self).create(vals)
        return detail

    def _constrains_date_start(self):
        return

    def _onchange_date_date_end(self):
        return
