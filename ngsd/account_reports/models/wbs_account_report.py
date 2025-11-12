from odoo import models, fields, api, _
from odoo.tools.misc import format_date, DEFAULT_SERVER_DATE_FORMAT
from datetime import timedelta, datetime, time
from odoo.tools import config, date_utils, get_lang, html2plaintext
from dateutil.relativedelta import relativedelta
from decimal import localcontext, Decimal, ROUND_HALF_UP
from pytz import timezone, UTC
import math
from odoo.addons.web.controllers.main import clean_action


class WbsAccountReportWizard(models.TransientModel):
    _name = "wbs.account.report.wizard"
    _description = "Báo cáo WBS"

    project_id = fields.Many2one(string='Dự án', comodel_name='project.project', required=True)
    wbs_id = fields.Many2one(string='Phiên bản', comodel_name='en.wbs', domain="[('project_id','=',project_id)]")
    finished_percent = fields.Float(string='% Hoàn thành kế hoạch', compute='_compute_finished_percent')
    en_progress = fields.Float(string='% Hoàn thành thực tế', compute='_compute_finished_percent')

    @api.depends('project_id', 'wbs_id')
    def _compute_finished_percent(self):
        with localcontext() as ctx:
            ctx.rounding = ROUND_HALF_UP
            for rec in self:
                a = 0
                b = 0
                total_en_progress = 0
                for stage in rec.wbs_id.project_stage_ids.filtered(lambda x: x.state != 'cancel'):
                    for c in stage.order_line.filtered(lambda x: not x.parent_id and x.state != 'cancel'):
                        a += c.technical_field_27058 * c.technical_field_27058a
                        b += c.technical_field_27058a
                        total_en_progress += c.en_progress * c.technical_field_27058a
                finished_percent = Decimal((a / b) * 100).to_integral_value(rounding=ROUND_HALF_UP) if b else 0
                en_progress = Decimal((total_en_progress / b) * 100).to_integral_value(rounding=ROUND_HALF_UP) if b else 0
                rec.finished_percent = finished_percent
                rec.en_progress = en_progress

    @api.onchange('project_id')
    def _onchange_project_id(self):
        self.wbs_id = self.project_id.en_current_version

    def do(self):
        self = self.sudo()
        total_hour_plan = 0
        total_hour = 0
        total_en_progress = 0
        for wp in self.wbs_id.workpackage_ids.filtered(lambda x: not x.parent_id and x.state != 'cancel'):
            total_hour_plan += wp.technical_field_27058a * wp.technical_field_27058
            total_hour += wp.technical_field_27058a
            total_en_progress += wp.en_progress * wp.technical_field_27058a

        en_plan = total_hour_plan / total_hour if total_hour else 0
        en_progress = total_en_progress / total_hour if total_hour else 0
        en_plan = Decimal(en_plan * 100).to_integral_value(rounding=ROUND_HALF_UP)
        en_progress = Decimal(en_progress * 100).to_integral_value(rounding=ROUND_HALF_UP)

        action = self.env.ref('account_reports.action_wbs_account_report').read()[0]
        action['target'] = 'main'
        action['context'] = {'model': 'wbs.account.report',
                             # 'date_from': self.date_from,
                             # 'date_to': self.date_to,
                             'project_id': self.project_id.id,
                             'wbs_id': self.wbs_id.id,
                             'finished_percent': en_plan,
                             'en_progress': en_progress
                             }
        return action


class WBSAccountReport(models.AbstractModel):
    _name = "wbs.account.report"
    _description = "Báo cáo WBS"
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
            {'name': '', 'style': 'min-width:50px;max-width:50px;background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;border:1px solid #000000'},
            {'name': 'Mã', 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap; border:1px solid #000000'},
            {'name': 'Nhiệm vụ', 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;'},
            {'name': 'Người chịu <br/>trách nhiệm', 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;'},
            {'name': 'Ngày bắt đầu<br/>kế hoạch', 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;'},
            {'name': 'Ngày kết thúc<br/>kế hoạch', 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;'},
            {'name': 'Giờ dự kiến', 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;'},
            {'name': 'Giờ thực tế', 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;'},
            {'name': '% Hoàn thành<br/>kế hoạch', 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;'},
            {'name': '% Hoàn thành<br/>thực tế', 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;'},
            {'name': 'Ngày bắt đầu<br/>thực tế', 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;'},
            {'name': 'Ngày kết thúc<br/>thực tế', 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;'},
            {'name': 'Mốc bàn giao', 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;'},
            {'name': 'Sản phẩm bàn<br/>giao', 'style': 'background-color:#3F4C6A;color:white;text-align:center; white-space:nowrap;'},
        ]
        return [columns_names]

    @api.model
    def _get_report_name(self):
        ctx = self._context
        project_id = ctx.get('project_id')
        wbs_id = ctx.get('wbs_id')
        finished_percent = ctx.get('finished_percent', 0)
        en_progress = ctx.get('en_progress', 0)
        report_period = ctx.get('report_period')
        return f'''
                     Dự án        : {self.env['project.project'].browse(project_id).display_name}<br/>
                  Phiên bản       : {self.env['en.wbs'].browse(wbs_id).version_number}<br/>
                  Kỳ báo cáo      : {report_period}<br/>
            % Hoàn thành kế hoạch : {min([int(finished_percent), 100])}%<br/>
            % Hoàn thành thực tế : {min([int(en_progress), 100])}%<br/>
        '''

    def _get_reports_buttons(self, options):
        return [
            # {'name': _('PDF'), 'sequence': 1, 'action': 'print_pdf', 'file_export_type': _('PDF')},
            {'name': _('XLSX'), 'sequence': 2, 'action': 'print_xlsx', 'file_export_type': _('XLSX')},
        ]

    def get_report_filename(self, options):
        return 'Báo cáo WBS'

    def _set_context(self, options):
        ctx = super()._set_context(options)
        project_id = ctx.get('project_id')
        wbs_id = ctx.get('wbs_id')
        finished_percent = ctx.get('finished_percent')
        en_progress = ctx.get('en_progress')
        report_period = ctx.get('report_period')
        if not project_id:
            wizard = self.env['wbs.account.report.wizard'].search([('create_uid', '=', self.env.user.id)], order='id desc', limit=1)
            project_id = wizard.project_id.id
            wbs_id = wizard.wbs_id.id
            finished_percent = wizard.finished_percent
            en_progress = wizard.en_progress

        ctx['project_id'] = project_id
        ctx['wbs_id'] = wbs_id
        ctx['finished_percent'] = finished_percent
        ctx['en_progress'] = en_progress
        ctx['report_period'] = report_period
        return ctx

    def _get_options(self, previous_options=None):
        res = super()._get_options(previous_options=previous_options)
        lst_key = ['project_id', 'wbs_id', 'finished_percent', 'en_progress', 'report_period']
        for k in lst_key:
            if k in self._context:
                res[k] = self._context.get(k)
            else:
                res[k] = previous_options.get(k) if previous_options else False
        return res

    @api.model
    def _get_lines(self, options, line_id=None):
        lines = []
        lg = self.env['res.lang']._lang_get(self.env.user.lang) or get_lang(self.env)
        ctx = self._context
        if self.env.user.has_group('ngsd_base.group_td'):
            self = self.sudo()
        project_id = options.get('project_id')
        wbs_id = options.get('wbs_id')
        finished_percent = options.get('finished_percent', 0)

        records = self.env['en.wbs'].browse(wbs_id)

        background = '#FFFFFF'
        with localcontext() as ctx:

            ctx.rounding = ROUND_HALF_UP
            project = self.env['project.project'].browse(project_id)
            padding = 0
            color = 'black'
            total_hour_plan = 0
            total_hour_effective = 0
            total_hour = 0
            total_en_progress = 0
            for wp in records.workpackage_ids.filtered(lambda x: not x.parent_id and x.state != 'cancel'):
                total_hour_plan += wp.technical_field_27058a * wp.technical_field_27058
                total_hour_effective += wp.effective_hours
                total_hour += wp.technical_field_27058a
                total_en_progress += wp.en_progress * wp.technical_field_27058a

            en_progress = total_en_progress / total_hour if total_hour else 0
            seconds = total_hour * 60 * 60
            minutes, seconds = divmod(seconds, 60)
            hours, minutes = divmod(minutes, 60)

            effective_seconds = total_hour_effective * 60 * 60
            effective_minutes, effective_seconds = divmod(effective_seconds, 60)
            effective_hours, effective_minutes = divmod(effective_minutes, 60)

            columns = [
                {'name': f"""<a data-id="{'project_%s' % project.id}" data-model="project.project" action="view_item" class="no_print oe_link_reports" style="border:unset;">Chi tiết</a>"""},
                {'name': project.en_code or '', 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                {'name': project.display_name or '', 'style': f'color:{color};padding-left:{padding}px;background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                {'name': '', 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                {'name': project.date_start.strftime(lg.date_format) if project.date_start else '', 'class': 'date', 'style': f'color:{color};background-color:{background};text-align:center;vertical-align:middle; white-space:nowrap;border:1px solid #000000;'},
                {'name': project.date.strftime(lg.date_format) if project.date else '', 'class': 'date', 'style': f'color:{color};background-color:{background};text-align:center;vertical-align:middle; white-space:nowrap;border:1px solid #000000;'},
                {'name': "%02d:%02d:%02d" % (hours, minutes, seconds), 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                {'name': "%02d:%02d:%02d" % (effective_hours, effective_minutes, effective_seconds), 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                {'name': f'{min([int(finished_percent), 100])}%', 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                {'name': f'{Decimal(en_progress * 100).to_integral_value(rounding=ROUND_HALF_UP)}%', 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                {'name': UTC.localize(project.en_real_start_date).astimezone(timezone(self.env.user.tz or 'UTC')).replace(tzinfo=None).strftime(f'{lg.date_format} {lg.time_format}') if project.en_real_start_date else '', 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                {'name': UTC.localize(project.en_real_end_date).astimezone(timezone(self.env.user.tz or 'UTC')).replace(tzinfo=None).strftime(f'{lg.date_format} {lg.time_format}') if project.en_real_end_date else '', 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                {'name': '', 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                {'name': '', 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
            ]

            lines += [{
                'id': 'project_%s' % project.id,
                'model': 'project.project',
                'name': '',
                'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000',
                'level': 1,
                'columns': columns,
                'unfoldable': False,
            }]
            for stage in records.mapped('project_stage_ids').filtered(lambda x: x.state != 'cancel'):
                if background == '#FFFFFF':
                    background = '#D8DAE0'
                else:
                    background = '#FFFFFF'
                padding = 0
                color = 'black'
                if stage.end_date and fields.Date.today() > stage.end_date and stage.state != 'done':
                    color = 'red'

                total_hour_plan = 0
                total_hour_effective = 0
                total_hour = 0
                total_en_progress = 0
                for wp in stage.order_line.filtered(lambda x: not x.parent_id and x.state != 'cancel'):
                    total_hour_plan += wp.technical_field_27058a * wp.technical_field_27058
                    total_hour_effective += wp.effective_hours
                    total_hour += wp.technical_field_27058a
                    total_en_progress += wp.en_progress * wp.technical_field_27058a

                en_plan = total_hour_plan / total_hour if total_hour else 0
                en_progress = total_en_progress / total_hour if total_hour else 0
                seconds = total_hour * 60 * 60
                minutes, seconds = divmod(seconds, 60)
                hours, minutes = divmod(minutes, 60)

                effective_seconds = total_hour_effective * 60 * 60
                effective_minutes, effective_seconds = divmod(effective_seconds, 60)
                effective_hours, effective_minutes = divmod(effective_minutes, 60)

                columns = [
                    {'name': f"""<a data-id="stage_{stage.id}" data-model="en.project.stage" action="view_item" class="no_print oe_link_reports" style="border:unset;">Chi tiết</a>"""},
                    {'name': stage.stage_code or '', 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                    {'name': stage.name or '', 'style': f'color:{color};padding-left:{padding}px;background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    {'name': '', 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                    {'name': stage.start_date.strftime(lg.date_format) if stage.start_date else '', 'class': 'date', 'style': f'color:{color};background-color:{background};text-align:center;vertical-align:middle; white-space:nowrap;border:1px solid #000000;'},
                    {'name': stage.end_date.strftime(lg.date_format) if stage.end_date else '', 'class': 'date', 'style': f'color:{color};background-color:{background};text-align:center;vertical-align:middle; white-space:nowrap;border:1px solid #000000;'},
                    {'name': "%02d:%02d:%02d" % (hours, minutes, seconds), 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                    {'name': "%02d:%02d:%02d" % (effective_hours, effective_minutes, effective_seconds), 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                    {'name': f'{Decimal(en_plan * 100).to_integral_value(rounding=ROUND_HALF_UP)}%', 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                    {'name': f'{Decimal(en_progress * 100).to_integral_value(rounding=ROUND_HALF_UP)}%', 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                    {'name': UTC.localize(stage.en_real_start_date).astimezone(timezone(self.env.user.tz or 'UTC')).replace(tzinfo=None).strftime(f'{lg.date_format} {lg.time_format}') if stage.en_real_start_date else '', 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                    {'name': UTC.localize(stage.en_real_end_date).astimezone(timezone(self.env.user.tz or 'UTC')).replace(tzinfo=None).strftime(f'{lg.date_format} {lg.time_format}') if stage.en_real_end_date else '', 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                    {'name': '<i class="fa fa-check-square-o"></i>' if stage.project_milestone else '', 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                    {'name': '', 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                ]

                lines += [{
                    'id': 'stage_%s' % stage.id,
                    'model': 'en.project.stage',
                    'name': '',
                    'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000',
                    'level': 1,
                    'columns': columns,
                    'unfoldable': True if stage.order_line.filtered(lambda x: not x.parent_id) else False,
                    'unfolded': self._need_to_unfold('stage_%s' % stage.id, options),
                }]
                wp_parent = stage.order_line.filtered(lambda x: not x.parent_id and x.state != 'cancel')
                padding_wp = padding
                for wp_child in wp_parent:
                    order_parent = wp_child
                    padding = padding_wp
                    while order_parent:
                        padding += 20
                        for line in order_parent:

                            color = 'black'
                            if line.date_end and fields.Date.today() > line.date_end and line.state != 'done':
                                color = 'red'

                            total_hour_plan = line.technical_field_27058a
                            total_hour_effective = line.effective_hours
                            seconds = total_hour_plan * 60 * 60
                            minutes, seconds = divmod(seconds, 60)
                            hours, minutes = divmod(minutes, 60)

                            effective_seconds = total_hour_effective * 60 * 60
                            effective_minutes, effective_seconds = divmod(effective_seconds, 60)
                            effective_hours, effective_minutes = divmod(effective_minutes, 60)

                            columns = [
                                {'name': f"""<a data-id="workpackage_{line.id}" data-model="en.workpackage" action="view_item" class="no_print oe_link_reports" style="border:unset;">Chi tiết</a>"""},
                                {'name': line.wp_code or '', 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                                {'name': line.name or '', 'style': f'color:{color};padding-left:{padding}px;background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                                {'name': line.user_id.display_name or '', 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                                {'name': line.date_start.strftime(lg.date_format) if line.date_start else '', 'class': 'date', 'style': f'color:{color};background-color:{background};text-align:center;vertical-align:middle; white-space:nowrap;border:1px solid #000000;'},
                                {'name': line.date_end.strftime(lg.date_format) if line.date_end else '', 'class': 'date', 'style': f'color:{color};background-color:{background};text-align:center;vertical-align:middle; white-space:nowrap;border:1px solid #000000;'},
                                {'name': "%02d:%02d:%02d" % (hours, minutes, seconds), 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                                {'name': "%02d:%02d:%02d" % (effective_hours, effective_minutes, effective_seconds), 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                                {'name': f'{Decimal(line.technical_field_27058 * 100).to_integral_value(rounding=ROUND_HALF_UP)}%', 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                                {'name': f'{Decimal(line.en_progress * 100).to_integral_value(rounding=ROUND_HALF_UP)}%', 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                                {'name': UTC.localize(line.en_real_start_date).astimezone(timezone(self.env.user.tz or 'UTC')).replace(tzinfo=None).strftime(f'{lg.date_format} {lg.time_format}') if line.en_real_start_date else '', 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                                {'name': UTC.localize(line.en_real_end_date).astimezone(timezone(self.env.user.tz or 'UTC')).replace(tzinfo=None).strftime(f'{lg.date_format} {lg.time_format}') if line.en_real_end_date else '', 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                                {'name': '<i class="fa fa-check-square-o"></i>' if line.pj_milestone else '', 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                                {'name': '<i class="fa fa-check-square-o"></i>' if line.handover_doc else '', 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                            ]

                            lines += [{
                                'id': f'workpackage_{line.id}',
                                'model': 'en.workpackage',
                                'parent_id': f'stage_{line.project_stage_id.id}' if not line.parent_id else f'workpackage_{line.parent_id.id}',
                                'name': '',
                                'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000',
                                'level': 1,
                                'columns': columns,
                                'unfoldable': True if line.child_ids else True if not line.child_ids and line.task_ids else False,
                                'unfolded': self._need_to_unfold(f'workpackage_{line.id}', options),
                            }]
                            child_padding = padding + 20
                            for task in line.task_ids.filtered(lambda x: x.stage_id.en_mark != 'b'):
                                seconds = task.planned_hours * 60 * 60
                                minutes, seconds = divmod(seconds, 60)
                                hours, minutes = divmod(minutes, 60)

                                effective_seconds = task.effective_hours * 60 * 60
                                effective_minutes, effective_seconds = divmod(effective_seconds, 60)
                                effective_hours, effective_minutes = divmod(effective_minutes, 60)

                                color = 'black'
                                if task.date_deadline and fields.Date.today() > task.date_deadline and task.stage_id.en_mark != 'g':
                                    color = 'red'

                                columns = [
                                    {'name': f"""<a data-id="task_{task.id}" data-model="project.task" action="view_item" class="no_print oe_link_reports" style="border:unset;">Chi tiết</a>"""},
                                    {'name': task.en_task_code or '', 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                                    {'name': task.name or '', 'style': f'color:{color};padding-left:{child_padding}px;background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                                    {'name': ', '.join(task.en_handler.mapped('display_name')) or '', 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                                    {'name': task.en_start_date.strftime(lg.date_format) if task.en_start_date else '', 'class': 'date', 'style': f'color:{color};background-color:{background};text-align:center;vertical-align:middle; white-space:nowrap;border:1px solid #000000;'},
                                    {'name': task.date_deadline.strftime(lg.date_format) if task.date_deadline else '', 'class': 'date', 'style': f'color:{color};background-color:{background};text-align:center;vertical-align:middle; white-space:nowrap;border:1px solid #000000;'},
                                    {'name': "%02d:%02d:%02d" % (hours, minutes, seconds), 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                                    {'name': "%02d:%02d:%02d" % (effective_hours, effective_minutes, effective_seconds), 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                                    {'name': f'{Decimal(task.technical_field_27058 * 100).to_integral_value(rounding=ROUND_HALF_UP)}%', 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                                    {'name': f'{Decimal(task.en_progress * 100).to_integral_value(rounding=ROUND_HALF_UP)}%', 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                                    {'name': UTC.localize(task.en_open_date).astimezone(timezone(self.env.user.tz or 'UTC')).replace(tzinfo=None).strftime(f'{lg.date_format} {lg.time_format}') if task.en_open_date else '', 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                                    {'name': UTC.localize(task.en_close_date).astimezone(timezone(self.env.user.tz or 'UTC')).replace(tzinfo=None).strftime(f'{lg.date_format} {lg.time_format}') if task.en_close_date else '', 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                                    {'name': '', 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                                    {'name': '', 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                                ]
                                lines += [{
                                    'id': f'task_{task.id}',
                                    'model': 'project.task',
                                    'parent_id': f'workpackage_{line.id}',
                                    'name': '',
                                    'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000',
                                    'level': 1,
                                    'columns': columns,
                                }]
                        order_parent = order_parent.mapped('child_ids')
        return lines

    # @api.model
    # def _get_templates(self):
    #     templates = super()._get_templates()
    #     templates['line_template'] = 'account_reports.line_template_wbs_account_report'
    #     return templates

    def view_item(self, options, params):
        id = None
        if params.get('id'):
            id = int(params.get('id').split('_')[1])
        action = self.env["ir.actions.actions"]
        if params.get('model') == 'project.project':
            action = self.env["ir.actions.actions"]._for_xml_id("ngsd_menu.open_view_project_all")
        if params.get('model') == 'en.project.stage':
            action = self.env["ir.actions.actions"]._for_xml_id("ngsd_base.project_stage_act")
        if params.get('model') == 'en.workpackage':
            action = self.env["ir.actions.actions"]._for_xml_id("ngsd_base.workpackage_act")
        if params.get('model') == 'project.task':
            action = self.env["ir.actions.actions"]._for_xml_id("project.action_view_all_task")
        action = clean_action(action, env=self.env)
        action['view_mode'] = 'form'
        action['views'] = [(False, 'form')]
        action['res_id'] = id
        action['context'] = {}
        action['target'] = 'main'

        return action
