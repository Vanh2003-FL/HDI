from email.policy import default

from odoo import models, fields, api, _
from odoo.tools.misc import format_date, DEFAULT_SERVER_DATE_FORMAT
from odoo.tools import config, date_utils, get_lang, html2plaintext
from decimal import localcontext, ROUND_HALF_UP
from pytz import timezone, UTC
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
from odoo.tools import float_round
import json


class WbsAccountReportWizard(models.TransientModel):
    _inherit = "wbs.account.report.wizard"

    project_id = fields.Many2one(string='Dự án', comodel_name='project.project', required=True, default=lambda self: self.env.context.get('default_project_id'))
    wbs_id = fields.Many2one(string='Phiên bản', comodel_name='en.wbs', domain="[('project_id','=', project_id), ('version_type', '=', 'baseline'), ('state', '=', 'approved')]")

    @api.depends('project_id', 'wbs_id')
    def _compute_finished_percent(self):
        for rec in self:
            rec.finished_percent = float_round(rec.wbs_id.plan_percent_completed * 100, precision_digits=1)
            rec.en_progress = float_round(rec.wbs_id.actual_percent_completed * 100, precision_digits=1)

    # report_period = fields.Selection(
    #     selection=lambda self: self._get_period_selection(),
    #     string="Kỳ báo cáo",
    #     help="Chọn kỳ báo cáo có trong dữ liệu snapshot.",
    #     required=True,
    #     default=lambda self: self._get_period_selection()[-1][0] if self._get_period_selection() else False,
    # )
    #
    # def _get_period_selection(self):
    #     self.env.cr.execute("""
    #         SELECT DISTINCT TRIM(period)
    #         FROM wbs_account_report_snapshot
    #         WHERE period IS NOT NULL AND TRIM(period) <> ''
    #     """)
    #     periods = [row[0] for row in self.env.cr.fetchall()]
    #
    #     # Luôn thêm tháng hiện tại nếu chưa có
    #     current_period = datetime.today().strftime('%m/%Y')
    #     if current_period not in periods:
    #         periods.append(current_period)
    #
    #     periods_sorted = sorted(periods, key=lambda p: datetime.strptime(p, '%m/%Y'))
    #     periods = [(p, p) for p in periods_sorted]
    #     return periods

    report_month = fields.Selection(
        selection=[
            ('01', 'Tháng 1'), ('02', 'Tháng 2'), ('03', 'Tháng 3'), ('04', 'Tháng 4'),
            ('05', 'Tháng 5'), ('06', 'Tháng 6'), ('07', 'Tháng 7'), ('08', 'Tháng 8'),
            ('09', 'Tháng 9'), ('10', 'Tháng 10'), ('11', 'Tháng 11'), ('12', 'Tháng 12'),
        ],
        string="Tháng",
        required=True,
        default=lambda self: date.today().strftime('%m')
    )

    report_year = fields.Selection(
        selection=[(str(y), str(y)) for y in range(2025, 2051)],
        string="Năm",
        required=True,
        default=lambda self: str(date.today().year)
    )

    @api.constrains('report_month', 'report_year')
    def _check_report_period(self):
        for rec in self:
            month = int(rec.report_month)
            year = int(rec.report_year)

            min_month = 10
            min_year = 2025

            if (year < min_year) or (year == min_year and month < min_month):
                raise UserError(_("Chỉ được phép lựa chọn xem báo cáo WBS từ tháng 10/2025 đến tháng hiện tại"))

            current_month = date.today().month
            current_year = date.today().year

            if (year > current_year) or (year == current_year and month > current_month):
                raise UserError(_("Chỉ được phép lựa chọn xem báo cáo WBS từ tháng 10/2025 đến tháng hiện tại"))

    def do(self):
        self = self.sudo()
        action = self.env.ref('account_reports.action_wbs_account_report').read()[0]

        formatted_period = False
        if self.report_month and self.report_year:
            formatted_period = f"{self.report_month}/{self.report_year}"
        else:
            formatted_period = (date.today() - relativedelta(months=1)).strftime('%m/%Y')

        action['target'] = 'main'
        action['context'] = {'model': 'wbs.account.report',
                             'project_id': self.project_id.id,
                             'wbs_id': self.wbs_id.id,
                             'finished_percent': self.finished_percent,
                             'en_progress': self.en_progress,
                             'report_period' : formatted_period}
        return action


class WBSAccountReport(models.AbstractModel):
    _inherit = "wbs.account.report"

    @api.model
    def _get_lines_others(self, options, line_id=None):
        lines = []
        lg = self.env['res.lang']._lang_get(self.env.user.lang) or get_lang(self.env)
        if self.env.user.has_group('ngsd_base.group_td'):
            self = self.sudo()
        project_id = options.get('project_id')
        wbs_id = options.get('wbs_id')
        wbs = self.env['en.wbs'].browse(wbs_id)
        background = '#FFFFFF'
        with localcontext() as ctx:
            ctx.rounding = ROUND_HALF_UP
            project = self.env['project.project'].browse(project_id)
            padding = 0
            color = 'black'
            plan_seconds = wbs.planned_hours * 60 * 60
            plan_minutes, plan_seconds = divmod(plan_seconds, 60)
            plan_hours, plan_minutes = divmod(plan_minutes, 60)
            actual_seconds = wbs.effective_hours * 60 * 60
            actual_minutes, actual_seconds = divmod(actual_seconds, 60)
            actual_hours, actual_minutes = divmod(actual_minutes, 60)
            plan_percent_completed = float_round(wbs.plan_percent_completed * 100, precision_digits=1)
            actual_percent_completed = float_round(wbs.actual_percent_completed * 100, precision_digits=1)
            if plan_percent_completed == int(plan_percent_completed):
                plan_percent_completed = int(plan_percent_completed)
            if actual_percent_completed == int(actual_percent_completed):
                actual_percent_completed = int(actual_percent_completed)
            columns = [
                {'name': f"""<a data-id="{'project_%s' % project.id}" data-model="project.project" action="view_item" class="no_print oe_link_reports" style="border:unset;">Chi tiết</a>"""},
                {'name': project.en_code or '',
                 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                {'name': project.display_name or '',
                 'style': f'color:{color};padding-left:{padding}px;background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                {'name': f'',
                 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                {'name': project.date_start.strftime(lg.date_format) if project.date_start else '', 'class': 'date',
                 'style': f'color:{color};background-color:{background};text-align:center;vertical-align:middle; white-space:nowrap;border:1px solid #000000;'},
                {'name': project.date.strftime(lg.date_format) if project.date else '', 'class': 'date',
                 'style': f'color:{color};background-color:{background};text-align:center;vertical-align:middle; white-space:nowrap;border:1px solid #000000;'},
                {'name': "%02d:%02d:%02d" % (plan_hours, plan_minutes, plan_seconds),
                 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                {'name': "%02d:%02d:%02d" % (actual_hours, actual_minutes, actual_seconds),
                 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                {'name': f'{plan_percent_completed}%',
                 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                {'name': f'{actual_percent_completed}%',
                 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                {'name': UTC.localize(project.en_real_start_date).astimezone(
                    timezone(self.env.user.tz or 'UTC')).replace(tzinfo=None).strftime(
                    f'{lg.date_format} {lg.time_format}') if project.en_real_start_date else '',
                 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                {'name': UTC.localize(project.en_real_end_date).astimezone(timezone(self.env.user.tz or 'UTC')).replace(
                    tzinfo=None).strftime(f'{lg.date_format} {lg.time_format}') if project.en_real_end_date else '',
                 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                {'name': '',
                 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                {'name': '',
                 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
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
            stages = wbs.wbs_task_ids.filtered(lambda x: x.category == "phase" and x.stage_id.en_mark != 'b').sorted(
                key=lambda x: (x.en_start_date, x.id))

            for stage in stages:
                background = '#D8DAE0' if background == '#FFFFFF' else '#FFFFFF'
                padding = 0
                color = 'black'
                if stage.date_deadline and fields.Date.today() > stage.date_deadline and stage.stage_id.en_mark != 'g':
                    color = 'red'
                plan_seconds = stage.planned_hours * 60 * 60
                plan_minutes, plan_seconds = divmod(plan_seconds, 60)
                plan_hours, plan_minutes = divmod(plan_minutes, 60)
                actual_seconds = stage.effective_hours * 60 * 60
                actual_minutes, actual_seconds = divmod(actual_seconds, 60)
                actual_hours, actual_minutes = divmod(actual_minutes, 60)
                plan_percent_completed = float_round(stage.plan_percent_completed * 100, precision_digits=1)
                actual_percent_completed = float_round(stage.actual_percent_completed * 100, precision_digits=1)
                if plan_percent_completed == int(plan_percent_completed):
                    plan_percent_completed = int(plan_percent_completed)
                if actual_percent_completed == int(actual_percent_completed):
                    actual_percent_completed = int(actual_percent_completed)
                columns = [
                    {
                        'name': f"""<a data-id="stage_{stage.id}" data-model="project.task" style="border:unset;"></a>"""},
                    {'name': stage.code or '',
                     'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                    {'name': stage.name or '',
                     'style': f'color:{color};padding-left:{padding}px;background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    {'name': f'{stage.en_handler.name or ""}',
                     'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                    {'name': stage.en_start_date.strftime(lg.date_format) if stage.en_start_date else '',
                     'class': 'date',
                     'style': f'color:{color};background-color:{background};text-align:center;vertical-align:middle; white-space:nowrap;border:1px solid #000000;'},
                    {'name': stage.date_deadline.strftime(lg.date_format) if stage.date_deadline else '',
                     'class': 'date',
                     'style': f'color:{color};background-color:{background};text-align:center;vertical-align:middle; white-space:nowrap;border:1px solid #000000;'},
                    {'name': "%02d:%02d:%02d" % (plan_hours, plan_minutes, plan_seconds),
                     'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                    {'name': "%02d:%02d:%02d" % (actual_hours, actual_minutes, actual_seconds),
                     'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                    {'name': f'{plan_percent_completed}%',
                     'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                    {'name': f'{actual_percent_completed}%',
                     'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                    {'name': stage.actual_start_date.strftime(lg.date_format) if stage.actual_start_date else '',
                     'class': 'date',
                     'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                    {'name': stage.actual_end_date.strftime(lg.date_format) if stage.actual_end_date else '',
                     'class': 'date',
                     'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                    {'name': '<i class="fa fa-check-square-o"></i>' if stage.is_project_milestone else '',
                     'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                    {'name': '<i class="fa fa-check-square-o"></i>' if stage.is_hand_over_document else '',
                     'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                ]
                lines += [{
                    'id': 'stage_%s' % stage.id,
                    'model': 'project.task',
                    'name': '',
                    'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000',
                    'level': 1,
                    'columns': columns,
                    'unfoldable': True if stage.child_ids.filtered(lambda x: x.stage_id.en_mark != 'b') else False,
                    'unfolded': self._need_to_unfold('stage_%s' % stage.id, options),
                }]

                packages = stage.child_ids.filtered(
                    lambda x: x.category == "package" and x.stage_id.en_mark != 'b').sorted(
                    key=lambda x: (x.en_start_date, x.id))
                for package in packages:
                    padding = 20
                    color = 'black'
                    if package.date_deadline and fields.Date.today() > package.date_deadline and package.stage_id.en_mark != 'g':
                        color = 'red'
                    plan_seconds = package.planned_hours * 60 * 60
                    plan_minutes, plan_seconds = divmod(plan_seconds, 60)
                    plan_hours, plan_minutes = divmod(plan_minutes, 60)

                    actual_seconds = package.effective_hours * 60 * 60
                    actual_minutes, actual_seconds = divmod(actual_seconds, 60)
                    actual_hours, actual_minutes = divmod(actual_minutes, 60)

                    plan_percent_completed = float_round(package.plan_percent_completed * 100, precision_digits=1)
                    actual_percent_completed = float_round(package.actual_percent_completed * 100, precision_digits=1)
                    if plan_percent_completed == int(plan_percent_completed):
                        plan_percent_completed = int(plan_percent_completed)
                    if actual_percent_completed == int(actual_percent_completed):
                        actual_percent_completed = int(actual_percent_completed)

                    columns = [
                        {
                            'name': f"""<a data-id="package_{package.id}" data-model="project.task" style="border:unset;"></a>"""},
                        {'name': f"{stage.code}/{package.code}" or '',
                         'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                        {'name': package.name or '',
                         'style': f'color:{color};padding-left:{padding}px;background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                        {'name': f'{package.en_handler.name or ""}',
                         'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                        {'name': package.en_start_date.strftime(lg.date_format) if package.en_start_date else '',
                         'class': 'date',
                         'style': f'color:{color};background-color:{background};text-align:center;vertical-align:middle; white-space:nowrap;border:1px solid #000000;'},
                        {'name': package.date_deadline.strftime(lg.date_format) if package.date_deadline else '',
                         'class': 'date',
                         'style': f'color:{color};background-color:{background};text-align:center;vertical-align:middle; white-space:nowrap;border:1px solid #000000;'},
                        {'name': "%02d:%02d:%02d" % (plan_hours, plan_minutes, plan_seconds),
                         'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                        {'name': "%02d:%02d:%02d" % (actual_hours, actual_minutes, actual_seconds),
                         'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                        {'name': f'{plan_percent_completed}%',
                         'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                        {'name': f'{actual_percent_completed}%',
                         'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                        {'name': package.actual_start_date.strftime(
                            lg.date_format) if package.actual_start_date else '',
                         'class': 'date',
                         'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                        {'name': package.actual_end_date.strftime(lg.date_format) if package.actual_end_date else '',
                         'class': 'date',
                         'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                        {'name': '<i class="fa fa-check-square-o"></i>' if package.is_project_milestone else '',
                         'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                        {'name': '<i class="fa fa-check-square-o"></i>' if package.is_hand_over_document else '',
                         'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                    ]
                    lines += [{
                        'id': 'package_%s' % package.id,
                        'model': 'project.task',
                        'parent_id': f'stage_{stage.id}',
                        'name': '',
                        'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000',
                        'level': 1,
                        'columns': columns,
                        'unfoldable': True if package.child_ids.filtered(
                            lambda x: x.stage_id.en_mark != 'b') else False,
                        'unfolded': self._need_to_unfold(f'package_{package.id}', options),
                    }]
                    child_packages = package.child_ids.filtered(
                        lambda x: x.category == "child_package" and x.stage_id.en_mark != 'b').sorted(
                        key=lambda x: (x.en_start_date, x.id))
                    for child_package in child_packages:
                        padding = 40
                        color = 'black'
                        if child_package.date_deadline and fields.Date.today() > child_package.date_deadline and child_package.stage_id.en_mark != 'g':
                            color = 'red'
                        plan_seconds = child_package.planned_hours * 60 * 60
                        plan_minutes, plan_seconds = divmod(plan_seconds, 60)
                        plan_hours, plan_minutes = divmod(plan_minutes, 60)

                        actual_seconds = child_package.effective_hours * 60 * 60
                        actual_minutes, actual_seconds = divmod(actual_seconds, 60)
                        actual_hours, actual_minutes = divmod(actual_minutes, 60)

                        plan_percent_completed = float_round(child_package.plan_percent_completed * 100, precision_digits=1)
                        actual_percent_completed = float_round(child_package.actual_percent_completed * 100, precision_digits=1)
                        if plan_percent_completed == int(plan_percent_completed):
                            plan_percent_completed = int(plan_percent_completed)
                        if actual_percent_completed == int(actual_percent_completed):
                            actual_percent_completed = int(actual_percent_completed)

                        columns = [
                            {
                                'name': f"""<a data-id="child_package_{child_package.id}" data-model="project.task" style="border:unset;"></a>"""},
                            {'name': f"{stage.code}/{package.code}/{child_package.code}" or '',
                             'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                            {'name': child_package.name or '',
                             'style': f'color:{color};padding-left:{padding}px;background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                            {'name': f'{child_package.en_handler.name or ""}',
                             'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                            {'name': child_package.en_start_date.strftime(
                                lg.date_format) if child_package.en_start_date else '',
                             'class': 'date',
                             'style': f'color:{color};background-color:{background};text-align:center;vertical-align:middle; white-space:nowrap;border:1px solid #000000;'},
                            {'name': child_package.date_deadline.strftime(
                                lg.date_format) if child_package.date_deadline else '',
                             'class': 'date',
                             'style': f'color:{color};background-color:{background};text-align:center;vertical-align:middle; white-space:nowrap;border:1px solid #000000;'},
                            {'name': "%02d:%02d:%02d" % (plan_hours, plan_minutes, plan_seconds),
                             'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                            {'name': "%02d:%02d:%02d" % (actual_hours, actual_minutes, actual_seconds),
                             'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                            {'name': f'{plan_percent_completed}%',
                             'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                            {'name': f'{actual_percent_completed}%',
                             'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                            {'name': child_package.actual_start_date.strftime(
                                lg.date_format) if child_package.actual_start_date else '', 'class': 'date',
                             'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                            {'name': child_package.actual_end_date.strftime(
                                lg.date_format) if child_package.actual_end_date else '',
                             'class': 'date',
                             'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                            {
                                'name': '<i class="fa fa-check-square-o"></i>' if child_package.is_project_milestone else '',
                                'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                            {
                                'name': '<i class="fa fa-check-square-o"></i>' if child_package.is_hand_over_document else '',
                                'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                        ]
                        lines += [{
                            'id': 'child_package_%s' % child_package.id,
                            'model': 'project.task',
                            'parent_id': f'package_{package.id}',
                            'name': '',
                            'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000',
                            'level': 1,
                            'columns': columns,
                            'unfoldable': True if child_package.child_ids.filtered(
                                lambda x: x.stage_id.en_mark != 'b') else False,
                            'unfolded': self._need_to_unfold('child_package_%s' % child_package.id, options),
                        }]
                        tasks = child_package.child_ids.filtered(
                            lambda x: x.category == "task" and x.stage_id.en_mark != 'b').sorted(
                            key=lambda x: (x.en_start_date, x.id))
                        for task in tasks:
                            padding = 60
                            color = 'black'
                            if task.date_deadline and fields.Date.today() > task.date_deadline and task.stage_id.en_mark != 'g':
                                color = 'red'
                            plan_seconds = task.planned_hours * 60 * 60
                            plan_minutes, plan_seconds = divmod(plan_seconds, 60)
                            plan_hours, plan_minutes = divmod(plan_minutes, 60)

                            actual_seconds = task.effective_hours * 60 * 60
                            actual_minutes, actual_seconds = divmod(actual_seconds, 60)
                            actual_hours, actual_minutes = divmod(actual_minutes, 60)

                            plan_percent_completed = float_round(task.plan_percent_completed * 100, precision_digits=1)
                            actual_percent_completed = float_round(task.actual_percent_completed * 100, precision_digits=1)
                            if plan_percent_completed == int(plan_percent_completed):
                                plan_percent_completed = int(plan_percent_completed)
                            if actual_percent_completed == int(actual_percent_completed):
                                actual_percent_completed = int(actual_percent_completed)

                            columns = [
                                {
                                    'name': f"""<a data-id="task_{task.id}" data-model="project.task" style="border:unset;"></a>"""},
                                {'name': f"{stage.code}/{package.code}/{child_package.code}/{task.code}" or '',
                                 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                                {'name': task.name or '',
                                 'style': f'color:{color};padding-left:{padding}px;background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                                {'name': f'{task.en_handler.name or ""}',
                                 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                                {'name': task.en_start_date.strftime(lg.date_format) if task.en_start_date else '',
                                 'class': 'date',
                                 'style': f'color:{color};background-color:{background};text-align:center;vertical-align:middle; white-space:nowrap;border:1px solid #000000;'},
                                {'name': task.date_deadline.strftime(lg.date_format) if task.date_deadline else '',
                                 'class': 'date',
                                 'style': f'color:{color};background-color:{background};text-align:center;vertical-align:middle; white-space:nowrap;border:1px solid #000000;'},
                                {'name': "%02d:%02d:%02d" % (plan_hours, plan_minutes, plan_seconds),
                                 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                                {'name': "%02d:%02d:%02d" % (actual_hours, actual_minutes, actual_seconds),
                                 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                                {'name': f'{plan_percent_completed}%',
                                 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                                {'name': f'{actual_percent_completed}%',
                                 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                                {'name': task.actual_start_date.strftime(
                                    lg.date_format) if task.actual_start_date else '', 'class': 'date',
                                 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                                {'name': task.actual_end_date.strftime(
                                    lg.date_format) if task.actual_end_date else '',
                                 'class': 'date',
                                 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                                {'name': '<i class="fa fa-check-square-o"></i>' if task.is_project_milestone else '',
                                 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                                {'name': '<i class="fa fa-check-square-o"></i>' if task.is_hand_over_document else '',
                                 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                            ]
                            lines += [{
                                'id': 'task_%s' % task.id,
                                'model': 'project.task',
                                'parent_id': f'child_package_{child_package.id}',
                                'name': '',
                                'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000',
                                'level': 1,
                                'columns': columns,
                                'unfoldable': False,
                                'unfolded': False,
                            }]
                    tasks = package.child_ids.filtered(
                        lambda x: x.category == "task" and x.stage_id.en_mark != 'b').sorted(
                        key=lambda x: (x.en_start_date, x.id))
                    if not child_packages:
                        for task in tasks:
                            padding = 40
                            color = 'black'
                            if task.date_deadline and fields.Date.today() > task.date_deadline and task.stage_id.en_mark != 'g':
                                color = 'red'
                            plan_seconds = task.planned_hours * 60 * 60
                            plan_minutes, plan_seconds = divmod(plan_seconds, 60)
                            plan_hours, plan_minutes = divmod(plan_minutes, 60)

                            actual_seconds = task.effective_hours * 60 * 60
                            actual_minutes, actual_seconds = divmod(actual_seconds, 60)
                            actual_hours, actual_minutes = divmod(actual_minutes, 60)

                            plan_percent_completed = float_round(task.plan_percent_completed * 100, precision_digits=1)
                            actual_percent_completed = float_round(task.actual_percent_completed * 100, precision_digits=1)
                            if plan_percent_completed == int(plan_percent_completed):
                                plan_percent_completed = int(plan_percent_completed)
                            if actual_percent_completed == int(actual_percent_completed):
                                actual_percent_completed = int(actual_percent_completed)

                            columns = [
                                {
                                    'name': f"""<a data-id="task_{task.id}" data-model="project.task" style="border:unset;"></a>"""},
                                {'name': f"{stage.code}/{package.code}/{task.code}" or '',
                                 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                                {'name': task.name or '',
                                 'style': f'color:{color};padding-left:{padding}px;background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                                {'name': f'{task.en_handler.name or ""}',
                                 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                                {'name': task.en_start_date.strftime(lg.date_format) if task.en_start_date else '',
                                 'class': 'date',
                                 'style': f'color:{color};background-color:{background};text-align:center;vertical-align:middle; white-space:nowrap;border:1px solid #000000;'},
                                {'name': task.date_deadline.strftime(lg.date_format) if task.date_deadline else '',
                                 'class': 'date',
                                 'style': f'color:{color};background-color:{background};text-align:center;vertical-align:middle; white-space:nowrap;border:1px solid #000000;'},
                                {'name': "%02d:%02d:%02d" % (plan_hours, plan_minutes, plan_seconds),
                                 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                                {'name': "%02d:%02d:%02d" % (actual_hours, actual_minutes, actual_seconds),
                                 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                                {'name': f'{plan_percent_completed}%',
                                 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                                {'name': f'{actual_percent_completed}%',
                                 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                                {'name': task.actual_start_date.strftime(
                                    lg.date_format) if task.actual_start_date else '', 'class': 'date',
                                 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                                {'name': task.actual_end_date.strftime(
                                    lg.date_format) if task.actual_end_date else '',
                                 'class': 'date',
                                 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                                {'name': '<i class="fa fa-check-square-o"></i>' if task.is_project_milestone else '',
                                 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                                {'name': '<i class="fa fa-check-square-o"></i>' if task.is_hand_over_document else '',
                                 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                            ]
                            lines += [{
                                'id': 'task_%s' % task.id,
                                'model': 'project.task',
                                'parent_id': f'package_{package.id}',
                                'name': '',
                                'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000',
                                'level': 1,
                                'columns': columns,
                                'unfoldable': False,
                                'unfolded': False,
                            }]
        return lines

    @api.model
    def _get_lines(self, options, line_id=None):
        project_id = options.get('project_id')
        wbs_id = options.get('wbs_id')
        report_period = options.get('report_period')

        snapshots = False

        min_snapshot = self.env['wbs.account.report.snapshot'].sudo().search([
            ('project_id', '=', project_id), #('wbs_id', '=', wbs_id),
        ], order='period asc', limit=1)

        if min_snapshot:

            p1 = datetime.strptime(min_snapshot.period, '%m/%Y')
            p2 = datetime.strptime(report_period, '%m/%Y')

            if p1 > p2:
                snapshots = self.env['wbs.account.report.snapshot'].sudo().search([
                    ('period', '=', min_snapshot.period), ('project_id', '=', project_id) #, ('wbs_id', '=', wbs_id)
                ], order='line_index')

        if not snapshots:
            snapshots = self.env['wbs.account.report.snapshot'].sudo().search([
                ('period', '=', report_period), ('project_id', '=', project_id) #, ('wbs_id', '=', wbs_id)
            ], order='line_index')

        if snapshots:
            lines = []
            for snap in snapshots:
                values = {
                    'id': snap.line_id,
                    'model': snap.model,
                    'parent_id': snap.parent_id,
                    'name': snap.name,
                    'style': snap.style,
                    'level': snap.level,
                    'unfoldable': snap.unfoldable,
                    'unfolded': snap.unfolded,
                }
                columns = [
                    {'name': snap.column_0, 'style': snap.column_0_style},
                    {'name': snap.column_1, 'style': snap.column_1_style},
                    {'name': snap.column_2, 'style': snap.column_2_style},
                    {'name': snap.column_3, 'style': snap.column_3_style},
                    {'name': snap.column_4, 'style': snap.column_4_style},
                    {'name': snap.column_5, 'style': snap.column_5_style},
                    {'name': snap.column_6, 'style': snap.column_6_style},
                    {'name': snap.column_7, 'style': snap.column_7_style},
                    {'name': snap.column_8, 'style': snap.column_8_style},
                    {'name': snap.column_9, 'style': snap.column_9_style},
                    {'name': snap.column_10, 'style': snap.column_10_style},
                    {'name': snap.column_11, 'style': snap.column_11_style},
                    {'name': snap.column_12, 'style': snap.column_12_style},
                    {'name': snap.column_13, 'style': snap.column_13_style}
                ]
                values['columns'] = columns
                lines.append(values)
            return lines
        else:
            return self._get_lines_others(options, line_id=None)


class WbsAccountReportSnapshot(models.Model):
    _name = 'wbs.account.report.snapshot'
    _inherit = "wbs.account.report"
    _description = 'WBS Account Report Snapshot'

    period = fields.Char(string='Kỳ báo cáo', required=True)
    line_index = fields.Integer(string='Thứ tự dòng', index=True)
    line_id = fields.Char(string='Line ID', required=True, index=True)
    project_id = fields.Integer(string='Project ID', required=True)
    wbs_id = fields.Integer(string='WBS ID', required=True)
    model = fields.Char(string='Model')
    parent_id = fields.Char(string='Parent ID')
    name = fields.Char(string='Name')
    style = fields.Text(string='Style')
    level = fields.Integer(string='Level')
    unfoldable = fields.Boolean(string='Unfoldable')
    unfolded = fields.Boolean(string='Unfolded')
    column_0 = fields.Char(string='Column_0')
    column_0_style = fields.Char(string='Column_0_style')
    column_1 = fields.Char(string='Column_1')
    column_1_style = fields.Char(string='Column_1_style')
    column_2 = fields.Char(string='Column_2')
    column_2_style = fields.Char(string='Column_2_style')
    column_3 = fields.Char(string='Column_3')
    column_3_style = fields.Char(string='Column_3_style')
    column_4 = fields.Char(string='Column_4')
    column_4_style = fields.Char(string='Column_4_style')
    column_5 = fields.Char(string='Column_5')
    column_5_style = fields.Char(string='Column_5_style')
    column_6 = fields.Char(string='Column_6')
    column_6_style = fields.Char(string='Column_6_style')
    column_7 = fields.Char(string='Column_7')
    column_7_style = fields.Char(string='Column_7_style')
    column_8 = fields.Char(string='Column_8')
    column_8_style = fields.Char(string='Column_8_style')
    column_9 = fields.Char(string='Column_9')
    column_9_style = fields.Char(string='Column_9_style')
    column_10 = fields.Char(string='Column_10')
    column_10_style = fields.Char(string='Column_10_style')
    column_11 = fields.Char(string='Column_11')
    column_11_style = fields.Char(string='Column_11_style')
    column_12 = fields.Char(string='Column_12')
    column_12_style = fields.Char(string='Column_12_style')
    column_13 = fields.Char(string='Column_13')
    column_13_style = fields.Char(string='Column_13_style')

    # Hàm cron
    @api.model
    def _cron_generate_wbs_snapshots(self, project_ids: list = None):
        """
        Tạo snapshot WBS định kỳ theo tháng
        """
        period = (date.today() - relativedelta(months=1)).strftime('%m/%Y')   # Ví dụ: 10/2025

        # Xóa snapshot kỳ cũ nếu có để tránh trùng
        self.search([('period', '=', period)]).unlink()

        # Gọi lại logic tạo snapshot
        self._generate_wbs_snapshot_for_period(period, project_ids)

    @api.model
    def _generate_wbs_snapshot_for_period(self, period, project_ids: list = None):
        lines = []
        lg = self.env['res.lang']._lang_get(self.env.user.lang) or get_lang(self.env)
        # project_ids = self.env['project.project'].search([('id', '=', 1111), ('active', '=', True)])
        # project_ids = (self.env['project.project']
        #                .search([('id', '>=', 1111), ('active', '=', True), ('stage_id.en_state', '=', 'doing')]
        #                 , order='id'))
        if not project_ids:
            project_list_ids = (self.env['project.project']
                           .search([('active', '=', True), ('stage_id.en_state', '=', 'doing')]
                           , order='id'))
            project_ids = [p.id for p in project_list_ids]

        else:
            if not isinstance(project_ids, list):
                project_ids = project_ids.ids

        create_vals = []
        for project_id in project_ids:
            wbs = self.env['en.wbs'].search([('project_id', '=', project_id), ('version_type', '=', 'baseline'), ('state', '=', 'approved')])
            if wbs:
                wbs = wbs[0]
            else:
                continue
            background = '#FFFFFF'
            with localcontext() as ctx:
                ctx.rounding = ROUND_HALF_UP
                project = self.env['project.project'].browse(project_id)
                padding = 0
                color = 'black'
                plan_seconds = wbs.planned_hours * 60 * 60
                plan_minutes, plan_seconds = divmod(plan_seconds, 60)
                plan_hours, plan_minutes = divmod(plan_minutes, 60)
                actual_seconds = wbs.effective_hours * 60 * 60
                actual_minutes, actual_seconds = divmod(actual_seconds, 60)
                actual_hours, actual_minutes = divmod(actual_minutes, 60)
                plan_percent_completed = float_round(wbs.plan_percent_completed * 100, precision_digits=1)
                actual_percent_completed = float_round(wbs.actual_percent_completed * 100, precision_digits=1)
                if plan_percent_completed == int(plan_percent_completed):
                    plan_percent_completed = int(plan_percent_completed)
                if actual_percent_completed == int(actual_percent_completed):
                    actual_percent_completed = int(actual_percent_completed)
                columns = [
                    {
                        'name': f"""<a data-id="{'project_%s' % project.id}" data-model="project.project" action="view_item" class="no_print oe_link_reports" style="border:unset;">Chi tiết</a>"""},
                    {'name': project.en_code or '',
                     'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                    {'name': project.display_name or '',
                     'style': f'color:{color};padding-left:{padding}px;background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                    {'name': f'',
                     'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                    {'name': project.date_start.strftime(lg.date_format) if project.date_start else '', 'class': 'date',
                     'style': f'color:{color};background-color:{background};text-align:center;vertical-align:middle; white-space:nowrap;border:1px solid #000000;'},
                    {'name': project.date.strftime(lg.date_format) if project.date else '', 'class': 'date',
                     'style': f'color:{color};background-color:{background};text-align:center;vertical-align:middle; white-space:nowrap;border:1px solid #000000;'},
                    {'name': "%02d:%02d:%02d" % (plan_hours, plan_minutes, plan_seconds),
                     'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                    {'name': "%02d:%02d:%02d" % (actual_hours, actual_minutes, actual_seconds),
                     'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                    {'name': f'{plan_percent_completed}%',
                     'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                    {'name': f'{actual_percent_completed}%',
                     'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                    {'name': UTC.localize(project.en_real_start_date).astimezone(
                        timezone(self.env.user.tz or 'UTC')).replace(tzinfo=None).strftime(
                        f'{lg.date_format} {lg.time_format}') if project.en_real_start_date else '',
                     'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                    {'name': UTC.localize(project.en_real_end_date).astimezone(timezone(self.env.user.tz or 'UTC')).replace(
                        tzinfo=None).strftime(f'{lg.date_format} {lg.time_format}') if project.en_real_end_date else '',
                     'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                    {'name': '',
                     'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                    {'name': '',
                     'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
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
                stages = wbs.wbs_task_ids.filtered(lambda x: x.category == "phase" and x.stage_id.en_mark != 'b').sorted(
                    key=lambda x: (x.en_start_date, x.id))

                for stage in stages:
                    background = '#D8DAE0' if background == '#FFFFFF' else '#FFFFFF'
                    padding = 0
                    color = 'black'
                    if stage.date_deadline and fields.Date.today() > stage.date_deadline and stage.stage_id.en_mark != 'g':
                        color = 'red'
                    plan_seconds = stage.planned_hours * 60 * 60
                    plan_minutes, plan_seconds = divmod(plan_seconds, 60)
                    plan_hours, plan_minutes = divmod(plan_minutes, 60)
                    actual_seconds = stage.effective_hours * 60 * 60
                    actual_minutes, actual_seconds = divmod(actual_seconds, 60)
                    actual_hours, actual_minutes = divmod(actual_minutes, 60)
                    plan_percent_completed = float_round(stage.plan_percent_completed * 100, precision_digits=1)
                    actual_percent_completed = float_round(stage.actual_percent_completed * 100, precision_digits=1)
                    if plan_percent_completed == int(plan_percent_completed):
                        plan_percent_completed = int(plan_percent_completed)
                    if actual_percent_completed == int(actual_percent_completed):
                        actual_percent_completed = int(actual_percent_completed)
                    columns = [
                        {
                            'name': f"""<a data-id="stage_{stage.id}" data-model="project.task" style="border:unset;"></a>"""},
                        {'name': stage.code or '',
                         'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                        {'name': stage.name or '',
                         'style': f'color:{color};padding-left:{padding}px;background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                        {'name': f'{stage.en_handler.name or ""}',
                         'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                        {'name': stage.en_start_date.strftime(lg.date_format) if stage.en_start_date else '',
                         'class': 'date',
                         'style': f'color:{color};background-color:{background};text-align:center;vertical-align:middle; white-space:nowrap;border:1px solid #000000;'},
                        {'name': stage.date_deadline.strftime(lg.date_format) if stage.date_deadline else '',
                         'class': 'date',
                         'style': f'color:{color};background-color:{background};text-align:center;vertical-align:middle; white-space:nowrap;border:1px solid #000000;'},
                        {'name': "%02d:%02d:%02d" % (plan_hours, plan_minutes, plan_seconds),
                         'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                        {'name': "%02d:%02d:%02d" % (actual_hours, actual_minutes, actual_seconds),
                         'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                        {'name': f'{plan_percent_completed}%',
                         'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                        {'name': f'{actual_percent_completed}%',
                         'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                        {'name': stage.actual_start_date.strftime(lg.date_format) if stage.actual_start_date else '',
                         'class': 'date',
                         'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                        {'name': stage.actual_end_date.strftime(lg.date_format) if stage.actual_end_date else '',
                         'class': 'date',
                         'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                        {'name': '<i class="fa fa-check-square-o"></i>' if stage.is_project_milestone else '',
                         'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                        {'name': '<i class="fa fa-check-square-o"></i>' if stage.is_hand_over_document else '',
                         'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                    ]
                    lines += [{
                        'id': 'stage_%s' % stage.id,
                        'model': 'project.task',
                        'name': '',
                        'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000',
                        'level': 1,
                        'columns': columns,
                        'unfoldable': True if stage.child_ids.filtered(lambda x: x.stage_id.en_mark != 'b') else False,
                        'unfolded': True,
                    }]

                    packages = stage.child_ids.filtered(
                        lambda x: x.category == "package" and x.stage_id.en_mark != 'b').sorted(
                        key=lambda x: (x.en_start_date, x.id))
                    for package in packages:
                        padding = 20
                        color = 'black'
                        if package.date_deadline and fields.Date.today() > package.date_deadline and package.stage_id.en_mark != 'g':
                            color = 'red'
                        plan_seconds = package.planned_hours * 60 * 60
                        plan_minutes, plan_seconds = divmod(plan_seconds, 60)
                        plan_hours, plan_minutes = divmod(plan_minutes, 60)

                        actual_seconds = package.effective_hours * 60 * 60
                        actual_minutes, actual_seconds = divmod(actual_seconds, 60)
                        actual_hours, actual_minutes = divmod(actual_minutes, 60)

                        plan_percent_completed = float_round(package.plan_percent_completed * 100, precision_digits=1)
                        actual_percent_completed = float_round(package.actual_percent_completed * 100, precision_digits=1)
                        if plan_percent_completed == int(plan_percent_completed):
                            plan_percent_completed = int(plan_percent_completed)
                        if actual_percent_completed == int(actual_percent_completed):
                            actual_percent_completed = int(actual_percent_completed)

                        columns = [
                            {
                                'name': f"""<a data-id="package_{package.id}" data-model="project.task" style="border:unset;"></a>"""},
                            {'name': f"{stage.code}/{package.code}" or '',
                             'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                            {'name': package.name or '',
                             'style': f'color:{color};padding-left:{padding}px;background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                            {'name': f'{package.en_handler.name or ""}',
                             'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                            {'name': package.en_start_date.strftime(lg.date_format) if package.en_start_date else '',
                             'class': 'date',
                             'style': f'color:{color};background-color:{background};text-align:center;vertical-align:middle; white-space:nowrap;border:1px solid #000000;'},
                            {'name': package.date_deadline.strftime(lg.date_format) if package.date_deadline else '',
                             'class': 'date',
                             'style': f'color:{color};background-color:{background};text-align:center;vertical-align:middle; white-space:nowrap;border:1px solid #000000;'},
                            {'name': "%02d:%02d:%02d" % (plan_hours, plan_minutes, plan_seconds),
                             'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                            {'name': "%02d:%02d:%02d" % (actual_hours, actual_minutes, actual_seconds),
                             'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                            {'name': f'{plan_percent_completed}%',
                             'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                            {'name': f'{actual_percent_completed}%',
                             'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                            {'name': package.actual_start_date.strftime(
                                lg.date_format) if package.actual_start_date else '',
                             'class': 'date',
                             'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                            {'name': package.actual_end_date.strftime(lg.date_format) if package.actual_end_date else '',
                             'class': 'date',
                             'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                            {'name': '<i class="fa fa-check-square-o"></i>' if package.is_project_milestone else '',
                             'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                            {'name': '<i class="fa fa-check-square-o"></i>' if package.is_hand_over_document else '',
                             'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                        ]
                        lines += [{
                            'id': 'package_%s' % package.id,
                            'model': 'project.task',
                            'parent_id': f'stage_{stage.id}',
                            'name': '',
                            'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000',
                            'level': 1,
                            'columns': columns,
                            'unfoldable': True if package.child_ids.filtered(
                                lambda x: x.stage_id.en_mark != 'b') else False,
                            'unfolded': True,
                        }]
                        child_packages = package.child_ids.filtered(
                            lambda x: x.category == "child_package" and x.stage_id.en_mark != 'b').sorted(
                            key=lambda x: (x.en_start_date, x.id))
                        for child_package in child_packages:
                            padding = 40
                            color = 'black'
                            if child_package.date_deadline and fields.Date.today() > child_package.date_deadline and child_package.stage_id.en_mark != 'g':
                                color = 'red'
                            plan_seconds = child_package.planned_hours * 60 * 60
                            plan_minutes, plan_seconds = divmod(plan_seconds, 60)
                            plan_hours, plan_minutes = divmod(plan_minutes, 60)

                            actual_seconds = child_package.effective_hours * 60 * 60
                            actual_minutes, actual_seconds = divmod(actual_seconds, 60)
                            actual_hours, actual_minutes = divmod(actual_minutes, 60)

                            plan_percent_completed = float_round(child_package.plan_percent_completed * 100, precision_digits=1)
                            actual_percent_completed = float_round(child_package.actual_percent_completed * 100, precision_digits=1)
                            if plan_percent_completed == int(plan_percent_completed):
                                plan_percent_completed = int(plan_percent_completed)
                            if actual_percent_completed == int(actual_percent_completed):
                                actual_percent_completed = int(actual_percent_completed)

                            columns = [
                                {
                                    'name': f"""<a data-id="child_package_{child_package.id}" data-model="project.task" style="border:unset;"></a>"""},
                                {'name': f"{stage.code}/{package.code}/{child_package.code}" or '',
                                 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                                {'name': child_package.name or '',
                                 'style': f'color:{color};padding-left:{padding}px;background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                                {'name': f'{child_package.en_handler.name or ""}',
                                 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                                {'name': child_package.en_start_date.strftime(
                                    lg.date_format) if child_package.en_start_date else '',
                                 'class': 'date',
                                 'style': f'color:{color};background-color:{background};text-align:center;vertical-align:middle; white-space:nowrap;border:1px solid #000000;'},
                                {'name': child_package.date_deadline.strftime(
                                    lg.date_format) if child_package.date_deadline else '',
                                 'class': 'date',
                                 'style': f'color:{color};background-color:{background};text-align:center;vertical-align:middle; white-space:nowrap;border:1px solid #000000;'},
                                {'name': "%02d:%02d:%02d" % (plan_hours, plan_minutes, plan_seconds),
                                 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                                {'name': "%02d:%02d:%02d" % (actual_hours, actual_minutes, actual_seconds),
                                 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                                {'name': f'{plan_percent_completed}%',
                                 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                                {'name': f'{actual_percent_completed}%',
                                 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                                {'name': child_package.actual_start_date.strftime(
                                    lg.date_format) if child_package.actual_start_date else '', 'class': 'date',
                                 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                                {'name': child_package.actual_end_date.strftime(
                                    lg.date_format) if child_package.actual_end_date else '',
                                 'class': 'date',
                                 'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                                {
                                    'name': '<i class="fa fa-check-square-o"></i>' if child_package.is_project_milestone else '',
                                    'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                                {
                                    'name': '<i class="fa fa-check-square-o"></i>' if child_package.is_hand_over_document else '',
                                    'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                            ]
                            lines += [{
                                'id': 'child_package_%s' % child_package.id,
                                'model': 'project.task',
                                'parent_id': f'package_{package.id}',
                                'name': '',
                                'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000',
                                'level': 1,
                                'columns': columns,
                                'unfoldable': True if child_package.child_ids.filtered(
                                    lambda x: x.stage_id.en_mark != 'b') else False,
                                'unfolded': True,
                            }]
                            tasks = child_package.child_ids.filtered(
                                lambda x: x.category == "task" and x.stage_id.en_mark != 'b').sorted(
                                key=lambda x: (x.en_start_date, x.id))
                            for task in tasks:
                                padding = 60
                                color = 'black'
                                if task.date_deadline and fields.Date.today() > task.date_deadline and task.stage_id.en_mark != 'g':
                                    color = 'red'
                                plan_seconds = task.planned_hours * 60 * 60
                                plan_minutes, plan_seconds = divmod(plan_seconds, 60)
                                plan_hours, plan_minutes = divmod(plan_minutes, 60)

                                actual_seconds = task.effective_hours * 60 * 60
                                actual_minutes, actual_seconds = divmod(actual_seconds, 60)
                                actual_hours, actual_minutes = divmod(actual_minutes, 60)

                                plan_percent_completed = float_round(task.plan_percent_completed * 100, precision_digits=1)
                                actual_percent_completed = float_round(task.actual_percent_completed * 100, precision_digits=1)
                                if plan_percent_completed == int(plan_percent_completed):
                                    plan_percent_completed = int(plan_percent_completed)
                                if actual_percent_completed == int(actual_percent_completed):
                                    actual_percent_completed = int(actual_percent_completed)

                                columns = [
                                    {
                                        'name': f"""<a data-id="task_{task.id}" data-model="project.task" style="border:unset;"></a>"""},
                                    {'name': f"{stage.code}/{package.code}/{child_package.code}/{task.code}" or '',
                                     'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                                    {'name': task.name or '',
                                     'style': f'color:{color};padding-left:{padding}px;background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                                    {'name': f'{task.en_handler.name or ""}',
                                     'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                                    {'name': task.en_start_date.strftime(lg.date_format) if task.en_start_date else '',
                                     'class': 'date',
                                     'style': f'color:{color};background-color:{background};text-align:center;vertical-align:middle; white-space:nowrap;border:1px solid #000000;'},
                                    {'name': task.date_deadline.strftime(lg.date_format) if task.date_deadline else '',
                                     'class': 'date',
                                     'style': f'color:{color};background-color:{background};text-align:center;vertical-align:middle; white-space:nowrap;border:1px solid #000000;'},
                                    {'name': "%02d:%02d:%02d" % (plan_hours, plan_minutes, plan_seconds),
                                     'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                                    {'name': "%02d:%02d:%02d" % (actual_hours, actual_minutes, actual_seconds),
                                     'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                                    {'name': f'{plan_percent_completed}%',
                                     'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                                    {'name': f'{actual_percent_completed}%',
                                     'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                                    {'name': task.actual_start_date.strftime(
                                        lg.date_format) if task.actual_start_date else '', 'class': 'date',
                                     'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                                    {'name': task.actual_end_date.strftime(
                                        lg.date_format) if task.actual_end_date else '',
                                     'class': 'date',
                                     'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                                    {'name': '<i class="fa fa-check-square-o"></i>' if task.is_project_milestone else '',
                                     'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                                    {'name': '<i class="fa fa-check-square-o"></i>' if task.is_hand_over_document else '',
                                     'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                                ]
                                lines += [{
                                    'id': 'task_%s' % task.id,
                                    'model': 'project.task',
                                    'parent_id': f'child_package_{child_package.id}',
                                    'name': '',
                                    'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000',
                                    'level': 1,
                                    'columns': columns,
                                    'unfoldable': False,
                                    'unfolded': False,
                                }]
                        tasks = package.child_ids.filtered(
                            lambda x: x.category == "task" and x.stage_id.en_mark != 'b').sorted(
                            key=lambda x: (x.en_start_date, x.id))
                        if not child_packages:
                            for task in tasks:
                                padding = 40
                                color = 'black'
                                if task.date_deadline and fields.Date.today() > task.date_deadline and task.stage_id.en_mark != 'g':
                                    color = 'red'
                                plan_seconds = task.planned_hours * 60 * 60
                                plan_minutes, plan_seconds = divmod(plan_seconds, 60)
                                plan_hours, plan_minutes = divmod(plan_minutes, 60)

                                actual_seconds = task.effective_hours * 60 * 60
                                actual_minutes, actual_seconds = divmod(actual_seconds, 60)
                                actual_hours, actual_minutes = divmod(actual_minutes, 60)

                                plan_percent_completed = float_round(task.plan_percent_completed * 100, precision_digits=1)
                                actual_percent_completed = float_round(task.actual_percent_completed * 100, precision_digits=1)
                                if plan_percent_completed == int(plan_percent_completed):
                                    plan_percent_completed = int(plan_percent_completed)
                                if actual_percent_completed == int(actual_percent_completed):
                                    actual_percent_completed = int(actual_percent_completed)

                                columns = [
                                    {
                                        'name': f"""<a data-id="task_{task.id}" data-model="project.task" style="border:unset;"></a>"""},
                                    {'name': f"{stage.code}/{package.code}/{task.code}" or '',
                                     'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                                    {'name': task.name or '',
                                     'style': f'color:{color};padding-left:{padding}px;background-color:{background};vertical-align:middle;text-align:left; white-space:nowrap;border:1px solid #000000'},
                                    {'name': f'{task.en_handler.name or ""}',
                                     'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                                    {'name': task.en_start_date.strftime(lg.date_format) if task.en_start_date else '',
                                     'class': 'date',
                                     'style': f'color:{color};background-color:{background};text-align:center;vertical-align:middle; white-space:nowrap;border:1px solid #000000;'},
                                    {'name': task.date_deadline.strftime(lg.date_format) if task.date_deadline else '',
                                     'class': 'date',
                                     'style': f'color:{color};background-color:{background};text-align:center;vertical-align:middle; white-space:nowrap;border:1px solid #000000;'},
                                    {'name': "%02d:%02d:%02d" % (plan_hours, plan_minutes, plan_seconds),
                                     'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                                    {'name': "%02d:%02d:%02d" % (actual_hours, actual_minutes, actual_seconds),
                                     'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                                    {'name': f'{plan_percent_completed}%',
                                     'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000'},
                                    {'name': f'{actual_percent_completed}%',
                                     'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                                    {'name': task.actual_start_date.strftime(
                                        lg.date_format) if task.actual_start_date else '', 'class': 'date',
                                     'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                                    {'name': task.actual_end_date.strftime(
                                        lg.date_format) if task.actual_end_date else '',
                                     'class': 'date',
                                     'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                                    {'name': '<i class="fa fa-check-square-o"></i>' if task.is_project_milestone else '',
                                     'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                                    {'name': '<i class="fa fa-check-square-o"></i>' if task.is_hand_over_document else '',
                                     'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:normal;border:1px solid #000000'},
                                ]
                                lines += [{
                                    'id': 'task_%s' % task.id,
                                    'model': 'project.task',
                                    'parent_id': f'package_{package.id}',
                                    'name': '',
                                    'style': f'color:{color};background-color:{background};vertical-align:middle;text-align:center; white-space:nowrap;border:1px solid #000000',
                                    'level': 1,
                                    'columns': columns,
                                    'unfoldable': False,
                                    'unfolded': False,
                                }]

            idx = 0
            for line in lines:
                values = {
                    'period': period,
                    'line_index': idx + 1,
                    'line_id': line.get('id'),
                    'wbs_id': wbs.id,
                    'project_id': project_id,
                    'model': line.get('model'),
                    'parent_id': line.get('parent_id'),
                    'name': line.get('name'),
                    'style': line.get('style'),
                    'level': line.get('level', 1),
                    'unfoldable': line.get('unfoldable', False),
                    'unfolded': line.get('unfolded', False),
                }

                # Gán các columns
                columns = line.get('columns', [])
                for i in range(14):
                    col_val = columns[i]['name'] if i < len(columns) else ''
                    values[f'column_{i}'] = col_val
                    if columns[i].get('style'):
                        col_val_style = columns[i]['style'] if i < len(columns) else ''
                        values[f'column_{i}_style'] = col_val_style
                create_vals.append(values)
                idx += 1
        self.env['wbs.account.report.snapshot'].create(create_vals)

class WBSAccountReport(models.AbstractModel):
    _inherit = "wbs.account.report"

    def _get_reports_buttons(self, options):
        buttons = super()._get_reports_buttons(options)
        buttons.append({
            'name': _('Chọn thông tin báo cáo'),
            'sequence': 3,
            'action': 'action_open_period_wizard',
            'type': 'object',  # quan trọng!
        })
        return buttons

    def action_open_period_wizard(self, options):
        project_id = options.get('project_id') if options else False
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wbs.account.report.wizard',
            'target': 'new',
            'views': [(False, 'form')],
            'view_mode': 'form',
            'context': {
                'default_project_id': project_id,
            },
        }