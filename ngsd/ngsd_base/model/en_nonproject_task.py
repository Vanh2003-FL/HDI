# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import ValidationError, UserError
from datetime import timedelta, datetime, time
from odoo.tools.date_utils import date_range
from dateutil.relativedelta import relativedelta
from pytz import timezone, UTC


class ENNonprojectTask(models.Model):
    _name = 'en.nonproject.task'
    _description = 'EN Nonproject Task'

    name = fields.Char('Tên công việc', required=1)
    en_department_id = fields.Many2one('hr.department', string='Việc thuộc về', required=True)

    en_task_type = fields.Selection([
        ('daily', 'Công việc hàng ngày'),
        ('support', 'Công việc kinh doanh'),
        ('waiting_task', 'Công việc trong dự án đang chờ'),
        ('presale', 'Công việc Presale'),
        ('support_project', 'Công việc hỗ trợ dự án')
    ], string='Loại việc')
    en_pic_id = fields.Many2one('res.users', string='Người chịu trách nhiệm', domain="[('employee_ids.department_id', '=', en_department_id)]", required=True)
    en_supervisor_id = fields.Many2one('res.users', string='Người giám sát', domain="[('id', 'in', en_supervisor_ids)]", required=True)
    en_supervisor_ids = fields.Many2many('res.users', compute='_compute_en_supervisor_ids', compute_sudo=True)
    en_pm_id = fields.Many2one('res.users', string='Người giám sát', domain="[('id', 'in', en_supervisor_ids)]", required=True)

    @api.constrains('en_pic_id', 'timesheet_ids')
    def _check_employee_timesheet_pic_id(self):
        for rec in self:
            for ts in rec.timesheet_ids:
                if ts.employee_id.user_id != rec.en_pic_id:
                    raise ValidationError('Nhân viên phải thuộc người chịu trách nhiệm')

    @api.depends('en_pic_id', 'en_department_id', 'en_task_type')
    def _compute_en_supervisor_ids(self):
        for rec in self:
            supervisor_ids = []
            if rec.en_task_type == 'waiting_task':
                supervisor_ids = self.env.ref('ngsd_base.group_pm').users.ids
            else:
                if rec.en_department_id.manager_id.user_id:
                    supervisor_ids.append(rec.en_department_id.manager_id.user_id.id)
                if rec.en_pic_id.employee_id.parent_id.user_id:
                    supervisor_ids.append(rec.en_pic_id.employee_id.parent_id.user_id.id)
            rec.en_supervisor_ids = [(6, 0, supervisor_ids)]

    @api.onchange('waiting_task')
    def change_waiting_task(self):
        for rec in self:
            if rec.en_task_type == 'waiting_task':
                rec.en_supervisor_id = False

    @api.onchange('en_department_id')
    def change_en_department_id(self):
        self = self.sudo()
        for rec in self:
            if rec.en_task_type != 'waiting_task' and rec.en_department_id.manager_id.user_id and rec.en_supervisor_id != rec.en_department_id.manager_id.user_id:
                rec.en_supervisor_id = rec.en_department_id.manager_id.user_id
            if rec.en_pic_id.employee_id.department_id != rec.en_department_id:
                rec.en_pic_id = False

    en_start_date = fields.Datetime(string="Ngày bắt đầu")
    en_end_date = fields.Datetime(string="Hạn hoàn thành")

    @api.constrains('en_end_date', 'en_start_date')
    def check_date(self):
        for rec in self:
            if rec.en_end_date and rec.en_start_date and rec.en_end_date < rec.en_start_date:
                raise UserError('Hạn hoàn thành không được sớm hơn Ngày bắt đầu!')

    en_state = fields.Selection([
        ('wait', 'Chờ thực hiện'),
        ('doing', 'Thực hiện'),
        ('done', 'Hoàn thành'),
    ], string='Trạng thái', default='wait')

    en_estimate_hour = fields.Float(string="Giờ dự kiến", compute='_compute_en_estimate_hour')
    en_fin_percentage = fields.Float(string="% hoàn thành")

    @api.constrains('en_fin_percentage')
    def _constrains_en_fin_percentage(self):
        for rec in self:
            if rec.en_fin_percentage < 0 or rec.en_fin_percentage > 1:
                raise ValidationError('% Hoàn thành chỉ được nhập trong khoảng 0 -> 100')

    @api.depends('en_start_date', 'en_end_date', 'en_pic_id')
    def _compute_en_estimate_hour(self):
        for rec in self:
            en_estimate_hour = 0
            if rec.en_start_date and rec.en_end_date and rec.en_pic_id.employee_id:
                user_tz = timezone(self.env.user.tz if self.env.user.tz else 'UTC')
                start_date = UTC.localize(rec.en_start_date).astimezone(user_tz).replace(tzinfo=None).date()
                end_date = UTC.localize(rec.en_end_date).astimezone(user_tz).replace(tzinfo=None).date()
                tech_data = self.env['en.technical.model'].convert_daterange_to_data(employee=rec.en_pic_id.employee_id, start_date=start_date, end_date=end_date)
                en_estimate_hour = sum([tech_data[d].get('number') for d in tech_data])
            rec.en_estimate_hour = en_estimate_hour

    timesheet_ids = fields.One2many('account.analytic.line', 'en_nonproject_task_id', string='Timesheet')

    def write(self, values):
        if values.get('en_state') and self.en_state == 'done':
            values['en_fin_percentage'] = 0
        if values.get('en_state') and values.get('en_state') == 'done':
            values['en_fin_percentage'] = 1
        if "en_fin_percentage" in values:
            return super(ENNonprojectTask, self.with_context(skip_timesheet_notify=True)).write(values)
        return super(ENNonprojectTask, self).write(values)

