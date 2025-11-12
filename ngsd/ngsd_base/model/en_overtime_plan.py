from odoo import *

READONLY_STATES = {
    'to_approve': [('readonly', True)],
    'approved': [('readonly', True)],
    'refused': [('readonly', True)],
}

class ENOvertimePlan(models.Model):
    _name = 'en.overtime.plan'
    _inherit = 'ngsd.approval'
    _description = 'Kế hoạch OT'

    name = fields.Char('Mã yêu cầu OT', default=lambda self: self.env['ir.sequence'].next_by_code('ngsd.base.ot.plan.code'), readonly=1, required=1)
    en_reason_ot = fields.Char(string='Lý do OT', states=READONLY_STATES)
    en_work_inproject = fields.Boolean(string='Công việc trong dự án', readonly=True)
    en_inf_hr_id = fields.Many2one('res.users', string='Gửi thông tin cho HR', states=READONLY_STATES)
    en_inf_user_id = fields.Many2one('res.users', string='Gửi thông tin cho', states=READONLY_STATES)
    state = fields.Selection(selection=[('draft', 'Chưa gửi'), ('to_approve', 'Đã gửi'), ('approved', 'Đã duyệt'), ('refused', 'Từ chối')], string='Trạng thái OT', required=1, default='draft')
    en_work_location = fields.Boolean('Làm việc tại văn phòng', default=True, states=READONLY_STATES)
    en_work_id = fields.Many2one('project.task', string='Công việc', domain="[('id', 'in', en_work_domain)]", states=READONLY_STATES)
    en_work_nonproject_id = fields.Many2one('en.nonproject.task', string='Công việc', domain="[('id', 'in', en_work_nonproject_domain)]", states=READONLY_STATES)
    en_date = fields.Date('Ngày OT', states=READONLY_STATES)
    en_hours = fields.Float('Số giờ OT', states=READONLY_STATES)
    en_workpackage_id = fields.Many2one(related='en_work_id.en_task_position')
    en_project_stage_id = fields.Many2one(related='en_workpackage_id.project_stage_id')
    en_time_used = fields.Float('Số giờ đã thực hiện', compute='_get_en_time_used', compute_sudo=True)
    en_reason_refuse = fields.Char(string='Lý do từ chối', copy=False, readonly=True)
    en_project_id = fields.Many2one('project.project', 'Dự án', domain="[('id', 'in', en_project_ids)]", states=READONLY_STATES)
    en_project_code = fields.Char(related='en_project_id.en_code')
    en_project_ids = fields.Many2many('project.project', compute='_search_project_of_create')
    en_work_domain = fields.Many2many('project.task', compute='_get_en_work_domain')
    department_id = fields.Many2one('hr.department', string='Trung tâm', related='create_uid.employee_id.department_id')

    @api.depends_context('uid')
    @api.depends('create_uid')
    def _search_project_of_create(self):
        for rec in self:
            rec.en_project_ids = self.env['project.project'].search([
                ('task_ids.en_handler', '=', rec.create_uid.id or self.env.user.id), ('task_ids.en_wbs_id.state', '=', 'approved')]).ids

    @api.onchange('en_project_id')
    def _onchange_en_project_id(self):
        for rec in self:
            rec.en_work_id = False

    @api.depends_context('uid')
    @api.depends('create_uid', 'en_project_id')
    def _get_en_work_domain(self):
        for rec in self:
            # rec.en_work_domain = self.env['project.task'].search([
            #     ('en_handler', '=', rec.create_uid.id or self.env.user.id),
            # ])
            rec.en_work_domain = False
            if not rec.en_project_id: continue
            task_ids = self.env['project.task'].search([
                ('en_handler', '=', rec.create_uid.id or self.env.user.id), ('project_id', '=', rec.en_project_id.id), ('stage_id.en_mark', 'in', ['a', 'c', 'f']), ('wbs_state', '=', 'approved')])
            rec.en_work_domain = task_ids.ids

    en_work_nonproject_domain = fields.Many2many('en.nonproject.task', compute='_get_en_work_nonproject_domain')

    @api.depends_context('uid')
    @api.depends('create_uid')
    def _get_en_work_nonproject_domain(self):
        for rec in self:
            rec.en_work_nonproject_domain = self.env['en.nonproject.task'].search([('en_pic_id', '=', rec.create_uid.id or self.env.user.id), ('en_state', 'in', ('wait', 'doing'))])

    @api.depends('en_work_id', 'en_work_inproject', 'en_work_nonproject_id')
    def _get_en_time_used(self):
        for rec in self:
            active_task = rec.en_work_id if rec.en_work_inproject else rec.en_work_nonproject_id
            rec.en_time_used = sum(active_task.timesheet_ids.ot_id.filtered(lambda o: o.state == 'approved').mapped('time'))

    def _callback_reason_refused(self, reason):
        self.write({'en_reason_refuse': reason})

    is_other_employee = fields.Boolean('Nhân viên phòng ban khác', compute='_get_is_other_employee', store=True)
    user_approved_ids = fields.Many2many('res.users', string='Những người đã duyệt', compute='_compute_user_approved_ids', compute_sudo=True)

    @api.depends('en_approve_line_ids', 'en_approve_line_ids.state')
    def _compute_user_approved_ids(self):
        for rec in self:
            rec.user_approved_ids = False
            for approve_line in rec.en_approve_line_ids:
                if approve_line.state == 'approved':
                    rec.user_approved_ids = [(4, approve_line.user_id.id)]

    @api.depends('create_uid', 'en_work_id')
    def _get_is_other_employee(self):
        for rec in self:
            rec.is_other_employee = rec.create_uid.employee_id.department_id.manager_id.user_id != rec.en_work_id.project_id.en_project_block_id

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        hide = ['en_last_approver_ids']
        res = super(ENOvertimePlan, self).fields_get()
        for field in hide:
            res[field]['searchable'] = False
            res[field]['sortable'] = False
            res[field]['exportable'] = False
        return res
