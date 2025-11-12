from odoo import models, fields, api, _
from odoo.tools.misc import format_date, DEFAULT_SERVER_DATE_FORMAT
from datetime import timedelta, datetime, time
from odoo.tools import config, date_utils, get_lang, html2plaintext
from dateutil.relativedelta import relativedelta
from decimal import localcontext, Decimal, ROUND_HALF_UP
from pytz import timezone
import math


class VersionAccountReportWizard(models.TransientModel):
    _name = "version.account.report.wizard"
    _description = "Chọn phiên bản so sánh"

    project_id = fields.Many2one(string='Dự án', related='current_wbs_id.project_id')
    current_wbs_id = fields.Many2one(string='Phiên bản hiện tại', comodel_name='en.wbs', readonly=True)
    compare_wbs_id = fields.Many2one(string='Phiên bản so sánh', comodel_name='en.wbs', required=True, domain="[('id','!=',current_wbs_id),('project_id','=',project_id)]")

    def do(self):
        self = self.sudo()
        action = self.env.ref('account_reports.action_version_account_report').read()[0]
        action['target'] = 'main'
        action['context'] = {'model': 'version.account.report',
                             # 'date_from': self.date_from,
                             # 'date_to': self.date_to,
                             'project_id': self.project_id.id,
                             'current_wbs_id': self.current_wbs_id.id,
                             'compare_wbs_id': self.compare_wbs_id.id,
                             }
        return action


class VersionAccountReport(models.AbstractModel):
    _name = "version.account.report"
    _description = "So sánh phiên bản WBS"
    _inherit = "account.report"

    # filter_date = {'mode': 'range', 'filter': 'this_month'}
    # filter_date = {'mode': 'single', 'filter': 'today'}
    filter_date = None
    filter_all_entries = None
    filter_journals = None
    filter_analytic = None
    filter_unfold_all = True

    @api.model
    def _get_columns(self, options):
        columns_names = [
            {'name': '', 'style': 'min-width:50px;max-width:50px;background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;border:1px solid #000000'},
            {'name': 'Mã', 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap; border:1px solid #000000'},
            {'name': 'Nhiệm vụ', 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;'},
            {'name': 'Người chịu <br/>trách nhiệm', 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;'},
            {'name': 'Ngày bắt đầu<br/>kế hoạch', 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;'},
            {'name': 'Ngày kết thúc<br/>kế hoạch', 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;'},
            {'name': 'Giờ dự kiến', 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;'},
            {'name': '% Hoàn thành<br/>kế hoạch', 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;'},
        ]
        return [columns_names]

    @api.model
    def _get_report_name(self):
        ctx = self._context
        project_id = ctx.get('project_id')
        current_wbs_id = ctx.get('current_wbs_id')
        compare_wbs_id = ctx.get('compare_wbs_id')
        return f'''
                   Dự án       : {self.env['project.project'].browse(project_id).display_name}<br/>
            Phiên bản hiện tại : {self.env['en.wbs'].browse(current_wbs_id).version_number}<br/>
            Phiên bản so sánh  : {self.env['en.wbs'].browse(compare_wbs_id).version_number}<br/>
        '''

    def _get_reports_buttons(self, options):
        return [
            # {'name': _('PDF'), 'sequence': 1, 'action': 'print_pdf', 'file_export_type': _('PDF')},
            # {'name': _('XLSX'), 'sequence': 2, 'action': 'print_xlsx', 'file_export_type': _('XLSX')},
        ]

    def _set_context(self, options):
        ctx = super()._set_context(options)
        project_id = ctx.get('project_id')
        current_wbs_id = ctx.get('current_wbs_id')
        compare_wbs_id = ctx.get('compare_wbs_id')
        if not project_id:
            wizard = self.env['version.account.report.wizard'].search([('create_uid', '=', self.env.user.id)], order='id desc', limit=1)
            project_id = wizard.project_id.id
            current_wbs_id = wizard.current_wbs_id.id
            compare_wbs_id = wizard.compare_wbs_id.id

        ctx['project_id'] = project_id
        ctx['current_wbs_id'] = current_wbs_id
        ctx['compare_wbs_id'] = compare_wbs_id
        return ctx

    @api.model
    def _get_lines(self, options, line_id=None):
        lines = []
        lg = self.env['res.lang']._lang_get(self.env.user.lang) or get_lang(self.env)
        ctx = self._context
        current_wbs_id = ctx.get('current_wbs_id')
        compare_wbs_id = ctx.get('compare_wbs_id')

        records = self.env['en.wbs'].browse([current_wbs_id, compare_wbs_id])

        background = '#FFFFFF'
        with localcontext() as ctx:
            ctx.rounding = ROUND_HALF_UP
            for stage_code in set(records.mapped('project_stage_ids.origin_code')):
                if background == '#FFFFFF':
                    background = '#D8DAE0'
                else:
                    background = '#FFFFFF'

                color = 'black'
                new_stage = self.env['en.project.stage'].search([('origin_code', '=', stage_code), ('wbs_version', '=', current_wbs_id)], limit=1)
                old_stage = self.env['en.project.stage'].search([('origin_code', '=', stage_code), ('wbs_version', '=', compare_wbs_id)], limit=1)
                if not new_stage:
                    color = 'red'
                if not old_stage:
                    color = 'green'
                stage = new_stage or old_stage
                padding = 0
                columns = [
                    {'name': stage.stage_code or '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                    {'name': stage.name or '', 'style': f'color:{color};padding-left:{padding}px;background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                    {'name': stage.start_date.strftime(lg.date_format) if stage.start_date else '', 'class': 'date', 'style': f'background-color:{background};text-align:center;vertical-align:middle; white-space:nowrap;border:1px solid #000000;'},
                    {'name': stage.end_date.strftime(lg.date_format) if stage.end_date else '', 'class': 'date', 'style': f'background-color:{background};text-align:center;vertical-align:middle; white-space:nowrap;border:1px solid #000000;'},
                    {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                    {'name': f'{Decimal((stage.technical_field_27058 * stage.technical_field_27058a / stage.technical_field_27058a) * 100).to_integral_value(rounding=ROUND_HALF_UP) if stage.technical_field_27058a else 0}%', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                ]

                lines += [{
                    'id': 'stage_%s' % stage.origin_code,
                    'name': '',
                    'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000',
                    'level': 1,
                    'columns': columns,
                    'unfoldable': True if stage.order_line.filtered(lambda x: not x.parent_id) else False,
                    'unfolded': self._need_to_unfold('stage_%s' % stage.origin_code, options),
                }]
                order_line_code = set(self.env['en.project.stage'].search([('origin_code', '=', stage_code), ('wbs_version', 'in', [current_wbs_id, compare_wbs_id])]).order_line.filtered(lambda x: not x.parent_id).mapped('origin_code'))
                while order_line_code:
                    padding += 20
                    new_lines = self.env['en.workpackage']
                    old_lines = self.env['en.workpackage']
                    for line_code in order_line_code:
                        color = 'black'
                        new_line = self.env['en.workpackage'].search([('origin_code', '=', line_code), ('project_stage_id.origin_code', '=', stage_code), ('wbs_version', '=', current_wbs_id)], limit=1)
                        old_line = self.env['en.workpackage'].search([('origin_code', '=', line_code), ('project_stage_id.origin_code', '=', stage_code), ('wbs_version', '=', compare_wbs_id)], limit=1)
                        new_lines |= new_line
                        old_lines |= old_line
                        if not new_line:
                            color = 'red'
                        if not old_line:
                            color = 'green'
                        line = new_line or old_line
                        columns = [
                            {'name': line.wp_code or '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                            {'name': line.name or '', 'style': f'color:{color};padding-left:{padding}px;background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                            {'name': line.user_id.display_name or '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                            {'name': line.date_start.strftime(lg.date_format) if line.date_start else '', 'class': 'date', 'style': f'background-color:{background};text-align:center;vertical-align:middle; white-space:nowrap;border:1px solid #000000;'},
                            {'name': line.date_end.strftime(lg.date_format) if line.date_end else '', 'class': 'date', 'style': f'background-color:{background};text-align:center;vertical-align:middle; white-space:nowrap;border:1px solid #000000;'},
                            {'name': '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                            {'name': f'{Decimal(line.technical_field_27058 * 100).to_integral_value(rounding=ROUND_HALF_UP)}%', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                        ]

                        lines += [{
                            'id': f'workpackage_{line.origin_code}',
                            'parent_id': f'stage_{line.project_stage_id.origin_code}' if not line.parent_id else f'workpackage_{line.parent_id.origin_code}',
                            'name': '',
                            'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000',
                            'level': 1,
                            'columns': columns,
                            'unfoldable': True if line.child_ids else True if not line.child_ids and line.task_ids else False,
                            'unfolded': self._need_to_unfold(f'workpackage_{line.origin_code}', options),
                        }]
                        task_ids = self.env['project.task'].search([('en_task_position', 'in', (new_line | old_line).ids)])
                        if task_ids:
                            child_padding = padding + 20
                            for task_code in set(task_ids.mapped('origin_code')):
                                color = 'black'
                                new_task = self.env['project.task'].search([('origin_code', '=', task_code), ('en_task_position.origin_code', '=', line_code), ('en_task_position.wbs_version', '=', current_wbs_id)], limit=1)
                                old_task = self.env['project.task'].search([('origin_code', '=', task_code), ('en_task_position.origin_code', '=', line_code), ('en_task_position.wbs_version', '=', compare_wbs_id)], limit=1)
                                if not new_task:
                                    color = 'red'
                                if not old_task:
                                    color = 'green'
                                task = new_task or old_task

                                seconds = task.planned_hours * 60 * 60
                                minutes, seconds = divmod(seconds, 60)
                                hours, minutes = divmod(minutes, 60)
                                columns = [
                                    {'name': task.en_task_code or '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                                    {'name': task.name or '', 'style': f'color:{color};padding-left:{child_padding}px;background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                                    {'name': ', '.join(task.en_handler.mapped('display_name')) or '', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                                    {'name': task.en_start_date.strftime(lg.date_format) if task.en_start_date else '', 'class': 'date', 'style': f'background-color:{background};text-align:center;vertical-align:middle; white-space:nowrap;border:1px solid #000000;'},
                                    {'name': task.date_deadline.strftime(lg.date_format) if task.date_deadline else '', 'class': 'date', 'style': f'background-color:{background};text-align:center;vertical-align:middle; white-space:nowrap;border:1px solid #000000;'},
                                    {'name': "%02d:%02d:%02d" % (hours, minutes, seconds), 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                                    {'name': f'{Decimal(task.technical_field_27058 * 100).to_integral_value(rounding=ROUND_HALF_UP)}%', 'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                                ]
                                lines += [{
                                    'id': f'task_{task.origin_code}',
                                    'parent_id': f'workpackage_{line_code}',
                                    'name': '',
                                    'style': f'background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000',
                                    'level': 1,
                                    'columns': columns,
                                }]

                    order_line_code = set(self.env['en.workpackage'].search([('parent_id', 'in', (new_lines | old_lines).ids)]).mapped('origin_code'))
        return lines
