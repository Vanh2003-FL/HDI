# -*- coding: utf-8 -*-
from pkg_resources import require

from odoo import models, fields, api, exceptions
from odoo.exceptions import ValidationError, UserError

READONLY_STATES = {
    'to_approve': [('readonly', True)],
    'approved': [('readonly', True)],
    'refused': [('readonly', True)],
}
EDIT_DRAFT_STATES = {
    'to_approve': [('readonly', True)],
    'approved': [('readonly', True)],
    'refused': [('readonly', True)],
    'expire': [('readonly', True)],
    'inactive': [('readonly', True)],
}

class ProjectDecision(models.Model):
    _name = 'project.decision'
    _description = 'Quyết định thành lập dự án'
    _inherit = 'ngsd.approval'
    _order = 'seq_id asc'

    @api.model
    def create(self, vals):
        # Tạo record project.decision trước
        decision = super(ProjectDecision, self).create(vals)

        if decision.project_id and not decision.en_resource_project_ids:
            decision._create_resource_snapshots()

        if decision.project_id and not decision.en_processing_rate_ids:
            decision._create_processing_rate_snapshots()

        if decision.project_id and not decision.en_response_rate_ids:
            decision._create_response_rate_snapshots()

        return decision

#Fields name
    parent_id = fields.Many2one(string='Thuộc về baseline', comodel_name='project.decision', compute_sudo=True,
                                compute='_compute_parent_id', store=True)
    version_number = fields.Char(string='Số phiên bản', compute_sudo=True, compute='_compute_version_number', store=True, copy=False)
    version_type = fields.Selection(string='Loại phiên bản', selection=[('baseline', 'Baseline'), ('plan', 'Plan')], store=True, compute_sudo=True, compute='_compute_version_type')
    state = fields.Selection(string='Trạng thái',
                             selection=[('draft', 'Nháp'),
                                        ('to_approve', 'Chờ duyệt'), ('approved', 'Đã duyệt'),
                                        ('refused', 'Bị từ chối'), ('inactive', 'Hết hiệu lực')], default='draft',
                             required=True, copy=False, store=True)

    v_decision_name = fields.Char(string='Quyết định', compute='_compute_decision_name_',store=True)

    @api.depends('version_number', 'version_type')
    def _compute_decision_name_(self):
        for rec in self:
            if rec.version_number.startswith("1.") and rec.version_type == 'baseline':
                rec.v_decision_name = 'Thành lập'
            else:
                if self.search([('project_id', '=', rec.project_id.id), ('version_type', '=', 'baseline'),('v_decision_name', '=', 'Thành lập'),('id', '>', rec.id)]):
                    rec.v_decision_name = 'Thành lập'
                else:
                    rec.v_decision_name = 'Điều chỉnh'
                if not self.search([('project_id', '=', rec.project_id.id), ('version_type', '=', 'baseline'),('v_decision_name', '=', 'Thành lập')]):
                    rec.v_decision_name = 'Thành lập'

    display_name = fields.Char(
        string='Tên hiển thị',
        compute='_compute_display_name',
        store=True
    )

    @api.depends('version_number', 'version_type')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.version_number} ({rec.version_type})" if rec.version_number and rec.version_type else rec.version_number or ""

    # Sử dụng field mới làm _rec_name
    _rec_name = 'display_name'

    # Mã dự án
    project_id = fields.Many2one(
        'project.project',
        string='Dự án',
        required=True,  # Nếu đây là trường bắt buộc
        ondelete='cascade'
    )

    #Thông tin dự án
    is_internal = fields.Boolean(string='Dự án nội bộ')
    en_level_project = fields.Many2one('en.project.level', string='Cấp độ dự án')
    en_area_id = fields.Many2one('en.name.area', string='Khu vực')
    en_block_id = fields.Many2one('en.name.block', string='Khối')
    en_department_id = fields.Many2one('hr.department', string='Trung tâm')
    en_project_type_id = fields.Many2one('en.project.type', string='Loại dự án')
    en_list_project_id = fields.Many2one('en.list.project', string='Danh mục dự án')
    en_project_model_id = fields.Many2one('en.project.model', string='Mô hình thực hiện dự án')
    date_start = fields.Date(string='Ngày bắt đầu')
    date_end = fields.Date(string='Ngày kết thúc')
    date = fields.Date(string='Ngày')
    en_real_start_date = fields.Datetime(string='Ngày bắt đầu thực tế')
    en_real_end_date = fields.Datetime(string='Ngày kết thúc thực tế')
    en_warranty_time = fields.Char(string='Thời gian bảo hành')

    #Quản lý
    # Giám đốc khối
    en_project_implementation_id = fields.Many2one('res.users', string='Giám đốc khối')

    # Giám đốc dự án
    en_project_manager_id = fields.Many2one('res.users', string='Giám đốc dự án')

    # Giám đốc Trung tâm
    en_project_block_id = fields.Many2one('res.users', string='Giám đốc Trung tâm')

    # Quản lý dự án
    user_id = fields.Many2one('res.users', string='Quản lý dự án')

    # Vice PM
    #en_project_vicepm_ids = fields.Many2many('res.users', string='Vice PM')
    en_project_vicepm_ids = fields.Many2many('res.users', relattion="project_project_en_project_vicepm_rel", string='Vice PM')

    # QA dự án
    en_project_qa_id = fields.Many2one('res.users', string='QA dự án')

    # Sales
    en_project_sale_id = fields.Many2one('res.users', string='Sales')

    # Kế toán
    en_project_accountant_id = fields.Many2one('res.users', string='Kế toán')

    # Pháp nhân ký HĐ
    en_contracting_entity = fields.Many2one('en.project.legal.entity', string='Pháp nhân ký HĐ')



    #Thông tin khách hàng
    # Loại khách hàng
    en_customer_type_id = fields.Many2one('en.customer.type', string='Loại khách hàng')

    # Khách hàng
    name_partner = fields.Char(string='Khách hàng')

    # Loại hợp đồng
    en_contract_type_id = fields.Many2one('project.type.source', string='Loại hợp đồng')

    # Số hợp đồng
    en_contract_number = fields.Char(string='Số hợp đồng')

    # Ngành
    en_branch_id = fields.Many2one('en.branch', string='Ngành')

    # Đơn vị tiền tệ
    currency_id = fields.Many2one('res.currency', string='Đơn vị tiền tệ')

    # Thời gian làm việc của khách hàng
    customer_resource_calendar_id = fields.Many2one('resource.calendar', string='Thời gian làm việc của khách hàng')

    # Chưa có hợp đồng
    en_no_contract = fields.Boolean(string='Chưa có hợp đồng')
    # Ngày bắt đầu hợp đồng
    en_contract_start_date = fields.Date(
        string="Ngày bắt đầu đầu dự kiến",
        related="project_id.en_contract_start_date",
        readonly=True,
        store=False
    )

    # Ngày kết thúc hợp đồng
    en_contract_end_date = fields.Date(
        string="Ngày kết thúc dự kiến",
        related="project_id.en_contract_end_date",
        readonly=True,
        store=False
    )


    #Thông tin chi tiết
    #BMM
    en_bmm = fields.Float(
        string='BMM',
        store=True,
        required=True,
        default=1.0,  # Giá trị mặc định > 0
        help="Giá trị phải lớn hơn 0"
    )
    # Tổng nguồn lực (MD)
    en_md_resource = fields.Float(string='Tổng nguồn lực (MD)')

    # Nguồn lực thực tế (MM)
    technical_field_28187 = fields.Char(string='Nguồn lực thực tế')

    # Kế hoạch nguồn lực
    en_resource_id = fields.Many2one('en.resource.planning', string='Kế hoạch nguồn lực')

    # Đơn vị quy đổi MM
    mm_rate = fields.Float(string='Đơn vị quy đổi MM')

    # MM quy đổi của dự án
    mm_conversion = fields.Float(string='MM quy đổi của dự án')

    # Phiên bản Wbs hiện tại
    en_current_version = fields.Many2one('en.wbs', string='Phiên bản Wbs hiện tại')

    # Hệ thống liên kết
    en_link_system = fields.Char(string='Hệ thống liên kết')

    # Hiển thị nút import
    show_import_button = fields.Boolean(string='Hiển thị nút import')

    reason_for_adjustment = fields.Text(string='Lý do điều chỉnh')

    vice_ceo = fields.Boolean(
        string="Phó tổng giám đốc",
        compute="_compute_need_vice_ceo",
        store=True,
        index=True,
    )

    # page
    # Pham vi du an
    en_project_goal = fields.Html(string="Mục tiêu dự án")
    en_business_scope = fields.Html(string="Phạm vi nghiệp vụ")
    en_implementation_scope = fields.Html(string="Phạm vi triển khai")
    en_other_scope = fields.Html(string="Phạm vi khác")

    #Nhân sự
    email = fields.Char(string='Email')
    department_id = fields.Boolean(string='Bộ phận')
    en_state = fields.Char(string='Trạng thái')
    date_leave = fields.Date(string='Ngày rời dự án')
    is_borrow = fields.Boolean(string='Nhân sự đi mượn')

    @api.depends("en_bmm", "project_id")
    def _compute_need_vice_ceo(self):
        """Tính toán xem có cần phó tổng giám đốc duyệt không"""
        for rec in self:
            rec.vice_ceo = rec.check_need_vice_ceo()

    def check_need_vice_ceo(self):
        """Kiểm tra BMM mới có vượt 115% baseline hay không"""
        self.ensure_one()
        project_id = self.project_id.id
        if not project_id:
            return False

        # Lấy baseline gần nhất
        self.env.cr.execute("""
                SELECT p.en_bmm
                FROM project_decision AS p
                WHERE p.project_id = %s
                  AND p.state = 'approved'
                  AND p.version_type = 'baseline'
                ORDER BY p.create_date DESC
                LIMIT 1;
            """, (project_id,))
        result = self.env.cr.fetchone()

        if not result:
            return False

        bmm_old = float(result[0]) or 0.0
        bm_new = float(self.en_bmm) or 0.0

        if bmm_old <= 0:
            return False

        percent = (bm_new / bmm_old) * 100
        return percent > 115

    @api.onchange('project_id')
    def _onchange_project_id(self):
        if self.project_id:
            fields_to_copy = [
                'is_internal',
                'en_level_project',
                'en_area_id',
                'en_block_id',
                'en_department_id',
                'en_project_type_id',
                'en_list_project_id',
                'en_project_model_id',
                'date_start',
                'date_end',
                'date',
                'en_real_start_date',
                'en_real_end_date',
                'en_warranty_time',
                'en_project_implementation_id',
                'en_project_manager_id',
                'en_project_block_id',
                'user_id',
                'en_project_vicepm_ids',
                'en_project_qa_id',
                'en_project_sale_id',
                'en_project_accountant_id',
                'en_contracting_entity',
                'en_customer_type_id',
                'name_partner',
                'en_contract_type_id',
                'en_contract_number',
                'en_branch_id',
                'currency_id',
                'customer_resource_calendar_id',
                'en_no_contract',
                "en_contract_start_date",
                "en_contract_end_date",
                'en_md_resource',
                'technical_field_28187',
                'en_resource_id',
                'mm_rate',
                'mm_conversion',
                'en_current_version',
                'en_link_system',
                'en_project_goal',
                'en_business_scope',
                'en_implementation_scope',
                'en_other_scope',
            ]
            project = self.project_id
            for field in fields_to_copy:
                if hasattr(project, field):
                    value = getattr(project, field)
                    field_obj = self._fields.get(field)
                    if field_obj:
                        if field_obj.type == 'many2one':
                            setattr(self, field, value.id if value else False)
                        elif field_obj.type == 'many2many':
                            setattr(self, field, [(6, 0, value.ids)] if value else [(6, 0, [])])
                        else:
                            setattr(self, field, value)


    en_resource_project_ids = fields.One2many('resource.project.snapshot', 'resource_decision_id',
                                              string='Danh sách nhân sự', store=True, copy=True)

    @api.onchange('project_id')
    def _onchange_project_resource(self):
        if not self.project_id: return
        en_resource_project_ids = []
        for resource in self.project_id.en_resource_project_ids:
            vals = (0, 0,
                        {'employee_id': resource.employee_id.id,
                         'type_id': resource.type_id.id if resource.type_id else False,
                         'email': resource.email,
                         'role_ids': [(6, 0, resource.role_ids.ids)],
                         'en_job_position_ids': [(6, 0, resource.en_job_position_ids.ids)],
                         'department_id': resource.department_id.id if resource.department_id else False,
                         'is_borrow': resource.is_borrow,
                         'date_leave': resource.date_leave,
                         'date_start': resource.date_start,
                         'date_end': resource.date_end,
                         'en_state': resource.en_state,
                         'state': resource.state,
                         },
                    )
            en_resource_project_ids.append(vals)
        self.en_resource_project_ids = en_resource_project_ids

    def _create_resource_snapshots(self):
        self.ensure_one()
        resource_snapshot = self.env['resource.project.snapshot']

        # Xóa các snapshot cũ nếu có
        self.en_resource_project_ids.unlink()

        # Tạo snapshot mới từ project
        for resource in self.project_id.en_resource_project_ids:
            resource_snapshot.create({
                'employee_id': resource.employee_id.id,
                'type_id': resource.type_id.id if resource.type_id else False,
                'role_ids': [(6, 0, resource.role_ids.ids)],
                'en_job_position_ids': [(6, 0, resource.en_job_position_ids.ids)],
                'department_id': resource.department_id.id if resource.department_id else False,
                'is_borrow': resource.is_borrow,
                'date_leave': resource.date_leave,
                'email': resource.email,
                'date_start': resource.date_start,
                'date_end': resource.date_end,
                'en_state': resource.en_state,
                'project_id': self.project_id.id,
                'resource_decision_id': self.id,
            })

    @api.constrains('en_bmm')
    def _check_en_bmm_positive(self):
        for record in self:
            if record.en_bmm <= 0:
                raise ValidationError("Giá trị BMM phải lớn hơn 0!")

    @api.depends('state')
    def _compute_version_type(self):
        for rec in self:
            version_type = 'plan'
            if rec.state in ['approved', 'inactive']:
            # if rec.state in ['approved', 'expire']:
                version_type = 'baseline'
            rec.version_type = version_type

    def action_open_new_tab(self):
        return self.open_form_or_tree_view('ngsc_project.project_decision_act', False, self, {'default_project_id': self.id})

    def button_to_approve(self):
        rslt = self.button_sent()
        if not rslt: return
        # if self.approver_id: self.send_notify(f'Bạn có kế hoạch {self.display_name} cần được duyệt', self.approver_id)
        self.write({'state': 'to_approve'})

    def button_sent(self):
        res = super().button_sent()
        return self.open_project_decision_or_not() or res

    def open_project_decision_or_not(self):
        if self._context.get('allow_active'):
            return self.open_form_or_tree_view('ngsd_base.project_decision_act', False, self, {'create': 0})
        return

    @api.depends('version_type', 'project_id', 'state')
    def _compute_parent_id(self):
        for rec in self:
            parent_id = self.env['project.decision']
            if rec.version_type == 'baseline': parent_id = False
            if rec.version_type == 'plan':
                parent_id = self.env['project.decision'].search(
                    [('version_type', '=', 'baseline'), ('project_id', '=', rec.project_id.id),
                     ('state', 'in', ['approved', 'inactive']), ('id', '<', rec._origin.id)], limit=1,
                    order='technical_field_before desc')
            rec.parent_id = parent_id

    child_ids = fields.One2many(string='Plan', comodel_name='project.decision', inverse_name='parent_id')
    technical_field_before = fields.Integer(string='🪙', compute_sudo=True, compute='_compute_technical_field_beter',
                                            store=True)
    technical_field_after = fields.Integer(string='🪙', compute_sudo=True, compute='_compute_technical_field_beter',
                                           store=True)

    @api.depends('version_number')
    def _compute_technical_field_beter(self):
        for rec in self:
            try:
                version_part = rec.version_number.split('.')
                rec.technical_field_before = int(version_part[0])
                rec.technical_field_after = int(version_part[1])
            except:
                rec.technical_field_before = 0
                rec.technical_field_after = 0

    seq_id = fields.Integer(string='💰', default=lambda self: int(self.env['ir.sequence'].next_by_code('seq.id')),
                            copy=False, store=True)

    @api.depends('project_id', 'project_id.project_decision_ids', 'parent_id', 'parent_id.child_ids', 'seq_id', 'version_type', 'state')
    def _compute_version_number(self):
        for parent in self.filtered(lambda x: x.parent_id).mapped("parent_id"):
            sequence = 1
            project_decision = parent.child_ids.filtered(lambda x: x.parent_id)
            for line in sorted(project_decision, key=lambda l: l.seq_id):
                line.version_number = f"{parent.technical_field_before}.{sequence}"
                sequence += 1
        for project in self.filtered(lambda x: not x.parent_id and x.version_type == 'plan').mapped("project_id"):
            sequence = 1
            project_decision = project.project_decision_ids.filtered(lambda x: not x.parent_id and x.version_type == 'plan')
            for line in sorted(project_decision, key=lambda l: l.seq_id):
                line.version_number = f"0.{sequence}"
                sequence += 1
        for project in self.filtered(lambda x: not x.parent_id and not x.version_type == 'plan').mapped("project_id"):
            sequence = 1
            project_decision = project.project_decision_ids.filtered(lambda x: not x.parent_id and not x.version_type == 'plan')
            for line in sorted(project_decision, key=lambda l: l.seq_id):
                line.version_number = f"{sequence}.0"
                sequence += 1

    #Cam ket ty le phan hoi
    en_processing_rate_ids = fields.One2many('en.processing.rate.snapshot', 'project_decision_id', string='Cam kết tỉ lệ xử lý')

    @api.onchange('project_id')
    def _onchange_project_processing_rate(self):
        if not self.project_id: return
        en_processing_rate_ids = []
        for resource in self.project_id.en_processing_rate_ids:
            vals = (0, 0,
                    {'start_date': resource.start_date,
                     'end_date': resource.end_date,
                     'rate': resource.rate,
                     },
                    )
            en_processing_rate_ids.append(vals)
        self.en_processing_rate_ids = en_processing_rate_ids

    def _create_processing_rate_snapshots(self):
        self.ensure_one()
        processing_rate_snapshot = self.env['en.processing.rate.snapshot']

        # Xóa các snapshot cũ nếu có
        self.en_processing_rate_ids.unlink()

        # Tạo snapshot mới từ project
        for resource in self.project_id.en_processing_rate_ids:
            processing_rate_snapshot.create({
                'start_date': resource.start_date,
                'end_date': resource.end_date,
                'rate': resource.rate,
                'project_decision_id': self.id,
            })

    #Cam kết tỷ lệ xử lý
    en_response_rate_ids = fields.One2many('en.response.rate.snapshot', 'project_decision_id', string='Cam kết tỉ lệ phản hồi')

    @api.onchange('project_id')
    def _onchange_project_response_rate(self):
        if not self.project_id: return
        en_response_rate_ids = []
        for resource in self.project_id.en_response_rate_ids:
            vals = (0, 0,
                    {'start_date': resource.start_date,
                     'end_date': resource.end_date,
                     'rate': resource.rate,
                     },
                    )
            en_response_rate_ids.append(vals)
        self.en_response_rate_ids = en_response_rate_ids

    def _create_response_rate_snapshots(self):
        self.ensure_one()
        response_rate_snapshot = self.env['en.response.rate.snapshot']

        # Xóa các snapshot cũ nếu có
        self.en_response_rate_ids.unlink()

        # Tạo snapshot mới từ project
        for resource in self.project_id.en_response_rate_ids:
            response_rate_snapshot.create({
                'start_date': resource.start_date,
                'end_date': resource.end_date,
                'rate': resource.rate,
                'project_decision_id': self.id,
            })

    technical_field_27768 = fields.Boolean(string='🚑', compute='_compute_technical_field_27768')

    @api.depends('state', 'project_id')
    def _compute_technical_field_27768(self):
        for rec in self:
            rec.technical_field_27768 = False
            if not rec.project_id:
                continue

            # Không cho phép tạo nếu đã tồn tại bản draft
            draft_count = self.env['project.decision'].search_count([
                ('project_id', '=', rec.project_id.id),
                ('state', '=', 'draft')
            ])
            if draft_count > 0:
                continue

            decisions = self.env['project.decision'].search([('project_id', '=', rec.project_id.id)])
            approved_count = len(decisions.filtered(lambda d: d.state == 'approved'))
            refused_or_inactive_count = len(decisions.filtered(lambda d: d.state in ['refused', 'inactive']))

            # Case 1: Chỉ có 1 bản 'approved', các bản còn lại chỉ là 'refused' hoặc 'inactive'
            if approved_count == 1 and all(d.state in ['approved', 'refused', 'inactive'] for d in decisions):
                if rec.state == 'approved':
                    rec.technical_field_27768 = True
            # Case 2: Tất cả đều là 'refused' hoặc 'inactive'
            elif len(decisions) == refused_or_inactive_count and rec.state in ['refused', 'inactive']:
                rec.technical_field_27768 = True

    created_by_project_decision_id = fields.Many2one('project.decision', readonly=1)

    def check_wbs_resource_planning(self):
        project_id = self.project_id.id
        en_wbs = self.env['en.wbs'].search([
            ('project_id', '=', project_id),
            ('state', '=', 'draft')
        ])

        en_resource_planning = self.env['en.resource.planning'].search([
            ('project_id', '=', project_id),
            ('state', '=', 'draft')
        ])
        if en_wbs or en_resource_planning:
            return True

    def button_duplicate_project_decision(self):
        if not self.technical_field_27768:
            raise UserError('QĐ TL Dự án này không được phép Tạo phiên bản mới')

        if self.check_need_vice_ceo() or self.check_wbs_resource_planning():
                raise UserError("Tồn tại KHNL/WBS đang ở trong trạng thái nháp; "
                                "yêu cầu Xóa/Hủy các bản này trước khi tạo QĐTLDA mới")

        self.ensure_one()
        if not self.project_id:
            raise UserError('Bản ghi này không có project cha.')
            # 👉 chỉ mở wizard
        return {
            "type": "ir.actions.act_window",
            "res_model": "project.decision.adjust.reason.wizard",
            "view_mode": "form",
            "target": "new",
            "name": "Lý do điều chỉnh",
            "context": {
                "default_old_decision_id": self.id,  # truyền bản ghi gốc vào wizard
            },
        }

    def button_duplicate_project_decision_no_vals(self):
        if not self.technical_field_27768:
            raise UserError('QĐ TL Dự án này không được phép Tạo phiên bản mới')
        new_project_decision = self.copy({'version_type': 'plan', 'created_by_project_decision_id': self.id, 'parent_id': self.parent_id.id or self.id})
        return self.open_create_project_decision_popup(new_project_decision)


    def open_create_project_decision_popup(self, project_decision):
        return {
            'name': 'Tạo phiên bản mới',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'views': [(self.env.ref('ngsc_project.project_decision_form_create_popup').id, 'form')],
            'view_id': self.env.ref('ngsc_project.project_decision_form_create_popup').id,
            'res_model': 'project.decision',
            'res_id': project_decision.id,
            'target': 'current',
            'context': {
                'create': 0,
                'active_test': False,
                'no_clean_inactive': True,
            }
        }

    def button_new_version_project_decision(self):
        if not self.technical_field_27768:
            raise UserError('QĐ TL Dự án này không được phép Tạo phiên bản mới')
        return {
            'name': 'Xác nhận',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'res_model': 'new.version.project.decision.wizard',
            'context': {
                'default_project_decision_id': self.id,
            },
            'target': 'new',
        }

    def button_approved(self):
        self = self.sudo()
        rslt = super().button_approved()


    def unlink(self):
        if any(rec.state in ['approved', 'inactive', 'refused', 'to_approve'] for rec in self):
            raise exceptions.UserError('Không cho phép xóa QĐ TL Dự án ở trạng thái khác Nháp')
        return super().unlink()

    def write(self, vals):
        res = super(ProjectDecision, self).write(vals)

        if 'state' in vals and vals['state'] == 'approved':
            for rec in self:
                # Tìm các record cùng project đã approved trước đó
                old_approved = self.env['project.decision'].search([
                    ('project_id', '=', rec.project_id.id),
                    ('state', '=', 'approved'),
                    ('id', '!=', rec.id)
                ])
                if old_approved:
                    old_approved.write({'state': 'inactive'})

        return res

    @api.depends_context('uid')
    @api.depends('create_uid', 'project_id.user_id', 'project_id.en_project_vicepm_ids')
    def _compute_sent_ok(self):
        user_id = self._uid
        for rec in self:
            project = rec.project_id
            rec.sent_ok = (user_id == rec.create_uid.id or user_id == project.user_id.id or user_id in project.en_project_vicepm_ids.ids)

class ProjectDecisionAdjustReason(models.TransientModel):
    _name = "project.decision.adjust.reason.wizard"
    _description = "Lý do điều chỉnh QĐTLDA"

    reason = fields.Text(string="Lý do điều chỉnh", required=True)
    old_decision_id = fields.Many2one("project.decision", string="QĐ gốc")

    def action_confirm(self):
        self.ensure_one()
        if not self.old_decision_id:
            raise UserError("Không tìm thấy quyết định cần điều chỉnh")

        project = self.old_decision_id.project_id
        fields_to_copy = [
            'is_internal',
            'en_level_project',
            'en_area_id',
            'en_block_id',
            'en_department_id',
            'en_project_type_id',
            'en_list_project_id',
            'en_project_model_id',
            'date_start',
            'date_end',
            'date',
            'en_real_start_date',
            'en_real_end_date',
            'en_warranty_time',
            'en_project_implementation_id',
            'en_project_manager_id',
            'en_project_block_id',
            'user_id',
            'en_project_vicepm_ids',
            'en_project_qa_id',
            'en_project_sale_id',
            'en_project_accountant_id',
            'en_contracting_entity',
            'en_customer_type_id',
            'name_partner',
            'en_contract_type_id',
            'en_contract_number',
            'en_branch_id',
            'currency_id',
            'customer_resource_calendar_id',
            'en_no_contract',
            "en_contract_start_date",
            "en_contract_end_date",
            'en_md_resource',
            'technical_field_28187',
            'en_resource_id',
            'mm_rate',
            'mm_conversion',
            'en_current_version',
            'en_link_system',
            'en_project_goal',
            'en_business_scope',
            'en_implementation_scope',
            'en_other_scope',
        ]
        vals = {'project_id': project.id}
        for field in fields_to_copy:
            if hasattr(project, field):
                val = getattr(project, field)
                field_obj = self.env['project.decision']._fields.get(field)
                if field_obj is not None:
                    if field_obj.type == 'many2one':
                        vals[field] = val.id if val else False
                    elif field_obj.type == 'many2many':
                        vals[field] = [(6, 0, val.ids)] if val else [(6, 0, [])]
                    else:
                        vals[field] = val

        vals['version_type'] = 'plan'
        vals['state'] = 'draft'
        vals['en_bmm'] = project.en_bmm
        vals['reason_for_adjustment'] = self.reason  # 👉 lưu lý do điều chỉnh luôn vào bản ghi mới
        # Tạo mới quyết định
        new_decision = self.env['project.decision'].create(vals)
        # snapshot
        new_decision._create_resource_snapshots()
        new_decision._create_processing_rate_snapshots()
        new_decision._create_response_rate_snapshots()

        return new_decision.open_create_project_decision_popup(new_decision)


