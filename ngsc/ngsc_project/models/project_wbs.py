from odoo import fields, models, api

from odoo.exceptions import ValidationError, UserError
from odoo.tools.misc import clean_context


class ProjectWbs(models.Model):
    _inherit = 'en.wbs'

    def get_default_en_resource_planning_latest(self):
        project_id = self._context.get('default_project_id', False)
        if not project_id:
            return self.env['en.resource.planning']
        en_wbs = self.env['en.resource.planning'].search([('project_id', '=', project_id),
                                                          ('state', '=', 'approved')], order='id desc', limit=1)
        return en_wbs

    start_date = fields.Date('Ngày bắt đầu', compute="_compute_start_date_end_date", store=True)
    end_date = fields.Date('Ngày kết thúc', compute="_compute_start_date_end_date", store=True)
    index_version = fields.Boolean("Phiên bản tính chỉ tiêu V2.0", store=True, copy=False)

    state = fields.Selection(string='Trạng thái',
                             selection=[('draft', 'Nháp'), ('waiting_create_resource_plan', 'Chờ tạo KHNL'),
                                        ('awaiting', 'Chờ duyệt'), ('waiting_resource_plan_approve', 'Chờ KHNL duyệt'),
                                        ('approved', 'Đã duyệt'), ('refused', 'Bị từ chối'),
                                        ('inactive', 'Hết hiệu lực'), ('cancel', 'Hủy')], default='draft', required=True, readonly=True,
                             copy=False)

    is_cancel_visible = fields.Boolean(
        string="Hiển thị nút Hủy",
        compute="_compute_is_cancel_visible"
    )

    @api.depends("state", "resource_planning_link_wbs", "resource_planning_link_wbs.state")
    def _compute_is_cancel_visible(self):
        for rec in self:
            if rec.state == "draft":
                rec.is_cancel_visible = True
            elif not rec.resource_planning_link_wbs and rec.state == "waiting_create_resource_plan":
                rec.is_cancel_visible = True
            else:
                rec.is_cancel_visible = False

    def button_en_cancel(self):
        for rec in self:
            rec.write({'state': 'cancel'})
        return True

    resource_planning_link_wbs = fields.Many2one(string='Kế hoạch nguồn lực', comodel_name='en.resource.planning',
                                                     compute_sudo=True, store=True,
                                                 default=get_default_en_resource_planning_latest)
    is_project_qa = fields.Boolean(string="Là QA dự án", compute='_compute_is_project_qa')

    #theo HĐ (readonly,project)
    en_contract_start_date = fields.Date(
        string="Ngày bắt đầu dự kiến theo HĐ",
        related="project_id.en_contract_start_date",
        readonly=True
    )
    en_contract_end_date = fields.Date(
        string="Ngày kết thúc dự kiến theo HĐ",
        related="project_id.en_contract_end_date",
        readonly=True
    )

    @api.depends("project_id")
    def _compute_is_project_qa(self):
        current_user = self.env.user
        for rec in self:
            if rec.project_id.en_project_qa_id == current_user or self.env.user.has_group('base.group_system'):
                rec.is_project_qa = True
            else:
                rec.is_project_qa = False

    @api.depends("project_stage_ids.start_date", "project_stage_ids.end_date")
    def _compute_start_date_end_date(self):
        for rec in self:
            if rec.project_stage_ids:
                rec.start_date = min(rec.project_stage_ids.mapped('start_date'))
                rec.end_date = max(rec.project_stage_ids.mapped('end_date'))
            else:
                rec.start_date = False
                rec.end_date = False

    def _constrains_workpackage_ids(self):
        # TODO 18/07/2025 các gói việc bắt đầu trước 01/07/2025 thì bỏ qua ràng buộc
        timeline_base = "2025-07-01"
        for rec in self:
            for r in rec.workpackage_ids.filtered(lambda x: not x.parent_id and x.en_start_date and str(x.en_start_date) >= timeline_base):
                if r.date_end and r.date_start:
                    duration = (r.date_end - r.date_start).days + 1
                    if duration > 45 and len(r.child_ids) < 2:
                        raise ValidationError(f"Gói công việc {r.name} phải có ít nhất 2 gói việc con. Vui lòng bổ sung thêm")

    def button_sent(self):
        self.project_stage_ids._en_constrains_en_start_date()
        self._constrains_workpackage_ids()
        self.workpackage_ids._constrains_date()
        self.write({'state': 'waiting_create_resource_plan'})
        return self.open_wbs_or_not()

    def button_approved(self):
        self = self.sudo()
        if self.state != 'awaiting':
            return None
        result = super().button_approved()
        if result:
            resource_plan = self.env['en.resource.planning'].search([('project_id', '=', self.project_id.id),
                ('state', 'not in', ('refused', 'expire', 'draft'))], order='id desc', limit=1)
            if resource_plan.state in ['to_wbs_approve', 'approved']:
                self.write({'seq_id': int(self.env['ir.sequence'].next_by_code('seq.id'))})
                self.sudo().write({'resource_planning_link_wbs': resource_plan.id})
                resource_plan.sudo().write({'state': 'approved'})
                self.search([('project_id', '=', self.project_id.id), ('id', '!=', self.id),
                             ('state', '=', 'approved')]).write({'state': 'inactive'})
                tasks = self.env['project.task'].search([('en_task_position', 'child_of', (
                            self.workpackage_ids | self.project_stage_ids.mapped('order_line')).ids)])
                for task in tasks:
                    task = task.sudo()
                    task.related_task_id.timesheet_ids.ot_id.write({'task_id': task.id})
                    task.related_task_id.timesheet_ids.write({'task_id': task.id})
                    self.env['en.overtime.plan'].sudo().search([('en_work_id', '=', task.related_task_id.id)]).write(
                        {'en_work_id': task.id})
            else:
                self.sudo().write({'state': 'waiting_resource_plan_approve'})
        return result

    def button_sent_from_resource_planing(self):
        self.project_stage_ids._en_constrains_en_start_date()
        self.workpackage_ids._constrains_date()
        if not self.sent_ok: return
        en_approve_line_ids, en_next_approver_ids = self.get_en_approve_line_ids()
        if not en_approve_line_ids: raise ValidationError(
            'Không tìm thấy quy trình duyệt tương ứng với chứng từ')
        self.with_context(clean_context(self._context)).write(
            {'en_request_user_id': self.env.user.id, 'en_request_date': fields.Datetime.now(),
             'state': self.sent_state(), 'en_next_approver_ids': [(6, 0, en_next_approver_ids.ids)],
             'en_approve_line_ids': [(5, 0, 0)] + en_approve_line_ids})
        self.state_notify(self.get_message())
        return True

    @api.constrains('index_version', 'project_id')
    def _check_unique_index_version_per_project(self):
        for rec in self:
            if rec.index_version and rec.project_id:
                count = self.search_count([
                    ('project_id', '=', rec.project_id.id),
                    ('index_version', '=', True),
                    ('id', '!=', rec.id)
                ])
                if count > 0:
                    raise ValidationError(
                        "Hiện đã tồn tại phiên bản WBS tính chỉ tiêu V2.0")

    def _callback_after_refused(self):
        resource_plan = self.env['en.resource.planning'].search([
            ('project_id', '=', self.project_id.id),
            ('state', 'not in', ('refused', 'expire', 'draft')),
        ], order='id desc', limit=1)

        if resource_plan:
            if resource_plan.state == 'to_approve' or resource_plan.state == 'to_wbs_approve':
                resource_plan.sudo().write({'state': 'refused'})

    def button_duplicate_wbs(self):
        if not self.technical_field_27795:
            raise UserError('WBS này không được phép Tạo phiên bản mới')
        self._check_resource_planing()
        newest_resource = self.env['en.resource.planning'].search([('project_id', '=', self.project_id.id), ('state', '=', 'approved')], order='id desc', limit=1)
        new_wbs = self.with_context(skip_constrains_start_deadline_date=True).copy({'version_type': 'plan', 'resource_plan_id': newest_resource.id, 'active': True, 'created_by_wbs_id': self.id, 'parent_id': self.parent_id.id or self.id})
        new_wbs.write({'resource_planning_link_wbs': newest_resource.id})
        for stage in self.project_stage_ids:
            stage.with_context(skip_constrains_start_deadline_date=True, newest_resource=newest_resource.id).copy({'wbs_version': new_wbs.id, 'wbs_version_old': self.id})
        return self.open_create_wbs_popup(new_wbs)

    def button_duplicate_wbs_no_vals(self):
        if not self.technical_field_27795:
            raise UserError('WBS này không được phép Tạo phiên bản mới')
        self._check_resource_planing()
        newest_resource = self.env['en.resource.planning'].search([('project_id', '=', self.project_id.id), ('state', '=', 'approved')], order='id desc', limit=1)
        new_wbs = self.copy({'version_type': 'plan', 'resource_plan_id': newest_resource.id, 'active': True, 'created_by_wbs_id': self.id, 'parent_id': self.parent_id.id or self.id})
        new_wbs.write({'resource_planning_link_wbs': newest_resource.id})
        return self.open_create_wbs_popup(new_wbs)


    def _check_resource_planing(self):
        _domain_resource_plan = [('project_id', '=', self.project_id.id), ('state', 'in', ('draft', 'to_approve'))]
        resource_plan = self.env['en.resource.planning'].sudo().search(_domain_resource_plan, order='id desc', limit=1)
        if resource_plan.state == "draft":
            raise ValidationError("Kế hoạch nguồn lực đang tồn tại phiên bản Nháp, "
                                  "vui lòng xóa bản ghi Kế hoạch nguồn lực đó để tiếp tục tạo WBS")
        if resource_plan.state == "to_approve":
            raise ValidationError("Kế hoạch nguồn lực đang tồn tại phiên bản Chờ duyệt, "
                                  "vui lòng hoàn tất duyệt/từ chối trước khi tạo WBS")