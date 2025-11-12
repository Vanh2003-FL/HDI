from odoo import api, fields, models
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from datetime import timedelta, datetime, time, date
from odoo.tools import config, date_utils, get_lang, html2plaintext

READONLY_STATES_1 = {
    'done': [('readonly', True)],
    'cancel': [('readonly', True)],
}

READONLY_STATES_2 = {
    'receive': [('readonly', True)],
    'no_receive': [('readonly', True)],
    'returned': [('readonly', True)],
}

class EnLenderEmployee(models.Model):
    _name = 'en.lender.employee'
    _description = 'Danh sách nhân sự cho mượn'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    code = fields.Char('Mã phiếu')
    date = fields.Date('Ngày', default=fields.Date.today(), states=READONLY_STATES_1)
    borrower_id = fields.Many2one('res.users', 'Người đi mượn', related='borrow_employee_id.borrower_id')
    department_borrower_id = fields.Many2one('hr.department', 'Trung tâm đi mượn', related='borrow_employee_id.department_borrower_id', store=True)
    lender_id = fields.Many2one('hr.employee', 'Người cho mượn', related='borrow_employee_id.lender_id')
    department_lender_id = fields.Many2one('hr.department', related='borrow_employee_id.department_lender_id', string='Trung tâm cho mượn', store=True)
    state = fields.Selection(string="Trạng thái", selection=[
        ('pending', 'Chưa bàn giao'),
        ('done', 'Đã bàn giao'),
        ('cancel', 'Hủy'),
        ], required=False, default='pending', tracking=True)
    borrow_employee_id = fields.Many2one('en.borrow.employee', 'Mã phiếu mượn', ondelete='cascade')
    lender_employee_ids = fields.One2many('en.lender.employee.detail', 'lender_employee_id', string='Chi tiết danh sách mượn', states=READONLY_STATES_1)
    is_borrower = fields.Boolean(compute='_compute_check_borrower')
    is_lender = fields.Boolean(compute='_compute_check_lender')

    @api.depends('borrower_id')
    def _compute_check_borrower(self):
        for rec in self:
            rec.is_borrower = False
            if rec.borrower_id == self.env.user:
                rec.is_borrower = True

    @api.depends('lender_id')
    def _compute_check_lender(self):
        for rec in self:
            rec.is_lender = False
            if rec.lender_id == self.env.user.employee_id:
                rec.is_lender = True

    def to_done(self):
        self.clear_caches()
        if any(not line.employee_id for line in self.lender_employee_ids):
            raise ValidationError('Dòng chi tiết đang chưa điền nhân viên')
        name_lender = self.lender_id.name
        if name_lender:
            self.send_notify(f'{name_lender} đã cho bạn mượn nhân sự. Bấm vào nút phía dưới để xem chi tiết.', self.borrower_id)
        else:
            self.send_notify(f'Người quản lý {self.department_lender_id.name} đã cho bạn mượn nhân sự', self.borrower_id)
        self.state = 'done'
        return True

    def to_cancel(self):
        self.lender_employee_ids.write({'state': 'no_receive'})
        self.state = 'cancel'

    # @api.constrains('lender_employee_ids')
    # def _constrains_overload(self):
    #     lg = self.env['res.lang']._lang_get(self.env.user.lang) or get_lang(self.env)
    #     for rec in self:
    #         groupby_overwork = {}
    #         for employee in set(rec.mapped('lender_employee_ids.employee_id')):
    #             if not employee.en_internal_ok: continue
    #             for line in rec.lender_employee_ids.filtered(lambda x: x.employee_id == employee):
    #                 employee_txt = f'Nhân viên {employee.display_name} đã bị quá workload vào ngày'
    #                 if employee_txt not in groupby_overwork:
    #                     groupby_overwork.setdefault(employee_txt, [])
    #                 datetime_start = datetime.combine(line.date_start, time.min)
    #                 datetime_end = datetime.combine(line.date_end, time.max)
    #                 if datetime_start > datetime_end: continue
    #                 for date_step in date_utils.date_range(datetime_start, datetime_end, relativedelta(days=1)):
    #                     if round(sum(self.env['en.lender.employee.detail'].search([('lender_employee_id', '=', rec.id), ('employee_id', '=', employee.id), '&', ('date_start', '<=', date_step.date()), ('date_end', '>=', date_step.date())]).mapped('workload')) + sum(self.env['en.resource.detail'].search([('order_id.state', '=', 'approved'),('employee_id', '=', employee.id), '&', ('date_start', '<=', date_step.date()), ('date_end', '>=', date_step.date())]).mapped('workload')), 10) <= 1.2: continue
    #                     if date_step.date() in groupby_overwork[employee_txt]: continue
    #                     groupby_overwork[employee_txt] += [date_step.date()]
    #         expt_txt = []
    #         for employee in groupby_overwork:
    #             if not groupby_overwork.get(employee, []): continue
    #             dated = sorted(groupby_overwork[employee])
    #             dated_txt = []
    #             min_dated = dated[0]
    #             max_dated = dated[0]
    #             for d in dated:
    #                 if max_dated == d or max_dated + relativedelta(days=1) == d:
    #                     max_dated = d
    #                     continue
    #                 if min_dated == max_dated:
    #                     dated_txt += [f'{max_dated.strftime(lg.date_format)}']
    #                 else:
    #                     dated_txt += [f'{min_dated.strftime(lg.date_format)} → {max_dated.strftime(lg.date_format)}']
    #                 min_dated = d
    #                 max_dated = d
    #             else:
    #                 if min_dated == max_dated:
    #                     dated_txt += [f'{max_dated.strftime(lg.date_format)}']
    #                 else:
    #                     dated_txt += [f'{min_dated.strftime(lg.date_format)} → {max_dated.strftime(lg.date_format)}']
    #             expt_txt += [f'{employee} {" và ".join(dated_txt)}']
    #         if expt_txt: raise ValidationError('\n'.join(expt_txt))

    def name_get(self):
        result = []
        for rec in self:
            if rec.department_borrower_id and rec.department_lender_id:
                result.append((rec.id, "%s mượn nhân sự %s" % (rec.department_borrower_id.name, rec.department_lender_id.name)))
            else:
                result.append((rec.id, "Mới"))
        return result

    @api.model
    def create(self, values):
        values['code'] = self.env['ir.sequence'].next_by_code('code.lender.employee')
        return super(EnLenderEmployee, self).create(values)

    def unlink(self):
        if any(rec.state != 'pending' for rec in self):
            raise ValidationError('Không được xóa các bản ghi ở trạng thái Đã bàn giao/Hủy')
        return super(EnLenderEmployee, self).unlink()


class EnLenderEmployeeDetail(models.Model):
    _name = 'en.lender.employee.detail'
    _description = 'Chi tiết danh sách nhân sự cho mượn'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'employee_id'

    employee_id = fields.Many2one('hr.employee', 'Tên nhân sự', states=READONLY_STATES_2, context={'active_test': False})
    email = fields.Char(related='employee_id.work_email', store=True, string='Email')
    job_position_id = fields.Many2one('en.job.position', 'Vị trí', domain="[('id', 'in', job_position_ids)]", required=True, states=READONLY_STATES_2)
    job_position_ids = fields.Many2many('en.job.position', string='Domain vị trí', compute='_compute_job_position')
    level_id = fields.Many2one('en.name.level', 'Cấp bậc', related='employee_id.en_level_id', store=True, readonly=True)
    date_start = fields.Date('Ngày bắt đầu', required=True, states=READONLY_STATES_2)
    date_end = fields.Date('Ngày kết thúc', required=True, states=READONLY_STATES_2)
    date_return = fields.Date('Ngày trả', compute='_get_date_return', store=True)

    @api.depends('date_end')
    def _get_date_return(self):
        for rec in self:
            if rec.date_end:
                rec.date_return = rec.date_end + relativedelta(days=1)
            else:
                rec.date_return = False

    workload = fields.Float('Workload', required=True, states=READONLY_STATES_2)
    description = fields.Text('Mô tả chi tiết', states=READONLY_STATES_2)
    state = fields.Selection(string="Trạng thái", selection=[
        ('new', 'Mới'),
        ('receive', 'Tiếp nhận'),
        ('no_receive', 'Không tiếp nhận'),
        ('returned', 'Đã trả'),
        ], required=False, default='new')
    lender_employee_id = fields.Many2one('en.lender.employee', 'Danh sách mượn nhân sự', ondelete='cascade')
    add_workload = fields.Float('Gửi duyệt YC tăng wl', default=False, copy=False, readonly=1)

    def action_send_mail_ahead_schedule(self):
        today = date.today()
        all_lender_employee_ids = self.search([('date_end', '=', today + relativedelta(days=7)), ('state', '=', 'receive')])
        for lender in all_lender_employee_ids:
            message = f"Nhân sự {lender.employee_id.name} sẽ kết thúc thời gian mượn vào ngày {lender.date_end.strftime('%d%m%Y')}"
            lender.lender_employee_id.send_notify(message, lender.lender_employee_id.borrower_id)

    def action_return_on_time(self):
        today = fields.Date.Date.context_today(self)
        list_lender_employee = self.search([('date_return', '<=', today), ('state', '=', 'receive')])
        for line in list_lender_employee:
            date_end = line.date_return - relativedelta(days=1)
            line.write({'state': 'returned'})
            message = f'{line.lender_employee_id.borrower_id.name} đã trả nhân sự {line.employee_id.name} ngày {line.date_return.strftime("%d/%m/%Y")} đúng hạn'
            line.lender_employee_id.send_notify(message, line.lender_employee_id.lender_id.user_id | line.lender_employee_id.borrower_id)
            line.lender_employee_id.message_post(body=message)
            if line.date_return == today:
                resource_project = self.env['resource.project'].search([('project_id.en_department_id', '=', self.lender_employee_id.department_borrower_id.id), ('employee_id', '=', line.employee_id.id), ('date_start', '>=', line.date_start), ('date_end', '<=', line.date_end), ('state', '=', 'active'), ('is_borrow', '=', True)])
                for resource in resource_project:
                    resource.action_leave(date_end)
            resource_department = self.env['en.department.resource'].search([('lender_employee_detail_id', '=', line.id)])
            resource_department.write({
                'state': 'returned',
                'date_end': date_end
            })

    def button_returned(self):
        date_return = fields.Date.Date.context_today(self)
        if self.date_start and self.date_start > date_return:
            date_return = self.date_start
        return {
            'name': 'Trả người',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'en.lender.employee.return.popup',
            'target': 'new',
            'context': {
                'default_detail_id': self.id,
                'default_date_return': date_return,
            },
        }

    def action_returned(self, date_return):
        user_lender = self.env.user
        resource_project = self.env['resource.project'].search(
            [('project_id.en_department_id', '=', self.lender_employee_id.department_borrower_id.id),
             ('employee_id', '=', self.employee_id.id),
             ('date_start', '>=', self.date_start),
             ('date_end', '>=', date_return),
             ('state', '=', 'active'),
             ('is_borrow', '=', True)])
        if resource_project:
            raise ValidationError('Bạn phải cho nhân sự đó rời dự án trước khi trả người')
        message = f'{user_lender.name} đã trả nhân sự {self.employee_id.name} ngày {date_return.strftime("%d/%m/%Y")}'
        self.lender_employee_id.send_notify(message, self.lender_employee_id.lender_id.user_id)
        self.lender_employee_id.message_post(body=message)
        vals = {
            'date_return': date_return,
        }
        if date_return <= fields.Date.Date.context_today(self):
            vals['state'] = 'returned'
            self.env['en.department.resource'].search([('lender_employee_detail_id', '=', self.id)]).write({
                'state': 'returned',
                'date_end': date_return - relativedelta(days=1)
            })
        self.write(vals)

    def button_receive(self):
        user_lender = self.env.user
        department_resource = self.env['en.department.resource'].search_count([('employee_id', '=', self.employee_id.id), ('lender_employee_detail_id.state', '!=', 'no_receive'), ('borrow_department_id', '=', self.lender_employee_id.department_borrower_id.id), ('date_start', '<=', self.date_end), ('date_end', '>=', self.date_start)])
        if department_resource:
            raise ValidationError(f'Nhân sự {self.employee_id.display_name} đã được mượn trong quãng thời gian này.')
        if self.lender_employee_id.lender_id:
            self.lender_employee_id.send_notify(f'{user_lender.name} đã tiếp nhận {self.employee_id.name}', self.lender_employee_id.lender_id.user_id)
        message = f'{user_lender.name} đã tiếp nhận {self.employee_id.name}'
        self.lender_employee_id.message_post(body=message)
        value = {
            'employee_id': self.employee_id.id,
            'job_position_id': self.job_position_id.id,
            'level_id': self.level_id.id,
            'workload': self.workload,
            'date_start': self.date_start,
            'date_end': self.date_end,
            'borrow_department_id': self.lender_employee_id.department_borrower_id.id,
            'lender_employee_detail_id': self.id
        }
        self.env['en.department.resource'].create(value)
        self.state = 'receive'

    def button_no_receive(self):
        user_lender = self.env.user
        if self.lender_employee_id.lender_id:
            self.lender_employee_id.send_notify(f'{user_lender.name} không tiếp nhận {self.employee_id.name}',self.lender_employee_id.lender_id.user_id)
        message = f'{user_lender.name} không tiếp nhận {self.employee_id.name}'
        self.lender_employee_id.message_post(body=message)
        self.state = 'no_receive'

    def button_en_copy(self):
        return self.copy({'employee_id': False})

    @api.depends('lender_employee_id', 'lender_employee_id.borrow_employee_id.borrow_employee_detail_ids')
    def _compute_job_position(self):
        for rec in self:
            rec.job_position_ids = False
            for line in rec.lender_employee_id.borrow_employee_id.borrow_employee_detail_ids:
                rec.job_position_ids = [(4, line.job_position_id.id)]

    @api.onchange('date_start', 'date_end')
    def _constrains_date_start_end(self):
        for rec in self:
            if rec.date_start and rec.date_end and rec.date_start > rec.date_end:
                raise ValidationError('Ngày bắt đầu không được lớn hơn ngày kết thúc')

    @api.onchange('workload')
    def _constrains_workload(self):
        for rec in self:
            if (rec.workload <= 0 or rec.workload > 1) and rec.workload:
                raise ValidationError('Workload phải nằm trong khoảng từ 1 đến 100%')

    @api.constrains('date_start', 'date_end', 'employee_id')
    def _constrains_date_no_duplicate(self):
        for rec in self:
            count_duplicate = self.search_count([
                ('employee_id', '=', rec.employee_id.id),
                ('id', '!=', rec.id),
                ('lender_employee_id.department_borrower_id', '=', rec.lender_employee_id.department_borrower_id.id),
                ('date_start', '<=', rec.date_end), ('date_end', '>=', rec.date_start),
                ('state', '!=', 'no_receive')
            ])
            if count_duplicate:
                raise ValidationError(f'Nhân sự {rec.employee_id.display_name} đã được cho {rec.lender_employee_id.department_borrower_id.display_name} mượn trong khoảng thời gian này. Vui lòng chọn lại thời gian hoặc nhân sự.')

    show_add_workload_request = fields.Boolean(compute='_compute_show_add_workload')
    show_add_workload_confirm = fields.Boolean(compute='_compute_show_add_workload')

    @api.depends_context('uid')
    @api.depends('add_workload')
    def _compute_show_add_workload(self):
        for rec in self:
            show_add_workload_request = False
            show_add_workload_confirm = False
            is_add_workload = rec.add_workload > 0
            if rec.state == 'receive' and not is_add_workload and self.env.user == rec.lender_employee_id.borrower_id:
                show_add_workload_request = True

            if rec.state == 'receive' and is_add_workload and self.env.user.employee_id == rec.lender_employee_id.lender_id:
                show_add_workload_confirm = True

            rec.show_add_workload_request = show_add_workload_request
            rec.show_add_workload_confirm = show_add_workload_confirm

    def add_workload_request(self):
        return {
            'name': 'Y/C tăng WL',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'add.workload.popup',
            'target': 'new',
            'context': {
                'default_detail_id': self.id,
                'default_type': 'request',
            },
        }

    def add_workload_confirm(self):
        return {
            'name': 'Y/C tăng WL',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'add.workload.popup',
            'target': 'new',
            'context': {
                'default_detail_id': self.id,
                'default_type': 'confirm',
                'default_add_workload': self.add_workload,
            },
        }

