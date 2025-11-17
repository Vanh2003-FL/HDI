from odoo import models, api, fields, _, exceptions

from dateutil.relativedelta import relativedelta
from datetime import datetime
import logging
_logger = logging.getLogger(__name__)


class HROverviewReportPopup(models.TransientModel):
    _name = 'hr.overview.report.popup'
    _description = 'Sơ đồ tổ chức phòng ban'

    en_area_ids = fields.Many2many(string='Khu vực', comodel_name='en.name.area')
    en_block_ids = fields.Many2many(string='Khối', comodel_name='en.name.block', domain="[('id', 'in', en_block_domain)]")
    en_department_ids = fields.Many2many(string='Trung tâm', comodel_name='hr.department', domain="[('id', 'in', en_department_domain)]")

    en_block_domain = fields.Many2many('en.name.block', string='Khối', compute='_get_en_block_domain')
    en_department_domain = fields.Many2many(string='Trung tâm', comodel_name='hr.department', compute='_get_en_department_domain')

    model = fields.Char(required=1)

    @api.onchange('en_area_ids')
    def change_en_area_ids(self):
        self.en_block_ids = False

    @api.onchange('en_block_ids')
    def change_en_block_ids(self):
        self.en_department_ids = False

    @api.depends('en_area_ids')
    def _get_en_block_domain(self):
        for rec in self:
            domain = []
            if rec.en_area_ids:
                domain = [('area_id', 'in', rec.en_area_ids.ids)]
            rec.en_block_domain = self.env['en.name.block'].search(domain)

    @api.depends('en_block_ids', 'en_area_ids')
    def _get_en_department_domain(self):
        for rec in self:
            domain = []
            if rec.en_area_ids:
                domain = [('block_id.area_id', 'in', rec.en_area_ids.ids)]
            if rec.en_area_ids:
                domain = [('block_id', 'in', rec.en_block_ids.ids)]
            rec.en_department_domain = self.env['hr.department'].search(domain)

    def button_confirm(self):
        if self.model == 'en.name.area':
            name = 'Sơ đồ tổ chức phòng ban'
        elif self.model == 'hr.org.chart.report':
            name = 'Sơ đồ tổ chức hình cây'
        else:
            name = 'Sơ đồ tổ chức'
        action = {
            'type': 'ir.actions.client',
            'name': name,
            # 'tag': 'hr_org_chart_overview',  # Module not available in Odoo 18
            'tag': 'display_notification',  # Temporary fallback
            'params': {
                'model': self.model,
            },
            'context': {
                'en_area_ids': self.en_area_ids.ids,
                'en_block_ids': self.en_block_ids.ids,
                'en_department_ids': self.en_department_ids.ids,
            },
            'target': 'main'
        }
        return action
