from odoo import models, api, fields, _, exceptions

from dateutil.relativedelta import relativedelta
from datetime import datetime
import logging
_logger = logging.getLogger(__name__)


class ReportInfoPopup(models.TransientModel):
    _name = 'report.info.popup'

    dest_name = fields.Char()
    dest_model = fields.Char()
    date_from = fields.Date('Từ', required=1)
    date_to = fields.Date('Đến', required=1)
    period = fields.Selection(selection=[
        ('optional', 'Tùy chọn'),
        ('this_month', 'Tháng này'),
        ('this_quarter', 'Quý này'),
        ('this_year', 'Năm nay'),
        ('this_week', 'Tuần này'),
        ('previous_month', 'Tháng trước'),
        ('previous_quarter', 'Quý trước'),
        ('previous_year', 'Năm trước'),
        ('previous_week', 'Tuần trước'),
        ('next_week', 'Tuần sau'),
    ], string='Kỳ báo cáo', required=1, default='this_month')

    en_area_ids = fields.Many2many(string='Khu vực', comodel_name='en.name.area')
    en_department_ids = fields.Many2many(string='Trung tâm', comodel_name='hr.department', domain="[('id', 'in', en_department_domain)]")
    project_ids = fields.Many2many('project.project', string='Dự án', domain="[('id', 'in', project_domain)]")

    en_department_domain = fields.Many2many(string='Trung tâm', comodel_name='hr.department', compute='_get_en_department_domain')
    project_domain = fields.Many2many('project.project', string='Dự án', compute='_get_project_domain')
    type_employee_ids = fields.Many2many('en.type', string='Loại nhân sự', domain="['|', ('en_internal', '=', True), ('is_os', '=', True)]")

    @api.onchange('en_area_ids')
    def change_en_area_ids(self):
        self.en_department_ids = False

    @api.onchange('en_department_ids')
    def change_en_department_ids(self):
        self.project_ids = False

    @api.depends('en_area_ids')
    def _get_en_department_domain(self):
        for rec in self:
            domain = []
            if rec.en_area_ids:
                domain = [('block_id.area_id', 'in', rec.en_area_ids.ids)]
            rec.en_department_domain = self.env['hr.department'].search(domain)

    @api.depends('en_area_ids', 'en_department_ids')
    def _get_project_domain(self):
        for rec in self:
            domain = [('stage_id.en_state', 'in', ['draft', 'doing', 'wait_for_execution'])]
            if rec.en_area_ids:
                domain += [('en_area_id', 'in', rec.en_area_ids.ids)]
            if rec.en_department_ids:
                domain += [('en_department_id', 'in', rec.en_department_ids.ids)]
            rec.project_domain = self.env['project.project'].search(domain)

    def button_confirm(self):
        ctx = {
            'create': 0,
            'delete': 0,
            'edit': 0,
            'export_xlsx': 0,
            'show_export_odoo_button': 1,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'report_info_popup_id': self.id,
        }
        if self.dest_model == 'project.status.report':
            ctx['en_area_ids'] = self.en_area_ids.ids
            ctx['en_department_ids'] = self.en_department_ids.ids
            ctx['project_ids'] = self.project_ids.ids
        if self.dest_model == 'busy.rate.report':
            ctx['type_employee_ids'] = self.type_employee_ids.ids
        self = self.with_context(**ctx)
        self.env[self.dest_model].init_data()
        if self.dest_model == 'resource.analysis.report':
            action = {
                'type': 'ir.actions.act_window',
                'name': self.dest_name + f" Từ {self.date_from.strftime('%d/%m/%Y')} đến {self.date_to.strftime('%d/%m/%Y')}",
                'res_model': self.dest_model,
                'views': [[False, 'list'],[False, 'pivot']],
                'domain': [('user_id', '=', self.env.user.id)],
                'context': ctx,
                'target': 'main'
            }
            return action
        action = {
            'type': 'ir.actions.act_window',
            'name': self.dest_name + f" Từ {self.date_from.strftime('%d/%m/%Y')} đến {self.date_to.strftime('%d/%m/%Y')}",
            'res_model': self.dest_model,
            'views': [[False, 'list']],
            'domain': [('user_id', '=', self.env.user.id)],
            'context': ctx,
            'target': 'main'
        }
        return action

    @api.onchange('period')
    def onchange_period(self):
        today = fields.Date.today()
        period = self.period
        if period == 'this_month':
            start_date = today.replace(day=1)
            end_date = today + relativedelta(months=1, day=1, days=-1)
        elif period == 'this_quarter':
            start_date = (today - relativedelta(months=(today.month - 1) % 3)).replace(day=1)
            end_date = today
        elif period == 'this_year':
            start_date = today.replace(month=1, day=1)
            end_date = today + relativedelta(month=1, day=1, years=1, days=-1)
        elif period == 'this_week':
            start_date = today + relativedelta(weeks=-1, days=1, weekday=0)
            end_date = today + relativedelta(weekday=6)
        elif period == 'previous_month':
            start_date = (today + relativedelta(months=-1)).replace(day=1)
            end_date = today + relativedelta(days=-today.day)
        elif period == 'previous_quarter':
            start_date = (today - relativedelta(months=(today.month - 1) % 3) - relativedelta(months=3)).replace(day=1)
            end_date = today - relativedelta(months=(today.month - 1) % 3) - relativedelta(days=today.day)
        elif period == 'previous_year':
            start_date = (today + relativedelta(years=-1)).replace(day=1, month=1)
            end_date = (today + relativedelta(years=-1)).replace(day=31, month=12)
        elif period == 'previous_week':
            start_date = today + relativedelta(weeks=-2, days=1, weekday=0)
            end_date = today + relativedelta(weeks=-1, weekday=6)
        elif period == 'next_week':
            start_date = today + relativedelta(weeks=0, days=1, weekday=0)
            end_date = today + relativedelta(weeks=1, weekday=6)
        else:
            start_date = datetime.strptime(self._context.get('start_date') or today.strftime('%Y-%m-%d'), '%Y-%m-%d')
            end_date = datetime.strptime(self._context.get('end_date') or today.strftime('%Y-%m-%d'), '%Y-%m-%d')
        self.date_from = start_date
        self.date_to = end_date

    @api.model
    def open_recent(self, old_id):
        old_record = self.browse(old_id)
        if old_record.exists() or self._context.get('default_dest_model'):
            return {
                'type': 'ir.actions.act_window',
                'name': old_record.dest_name or self._context.get('default_dest_name'),
                'res_model': 'report.info.popup',
                'views': [[self.env.ref('account_reports.report_info_popup_form').id, 'form']],
                'context': {'default_dest_model': old_record.dest_model or self._context.get('default_dest_model'), 'default_dest_name': old_record.dest_name or self._context.get('default_dest_name')},
                'res_id': old_record.id,
                'target': 'new',
            }
