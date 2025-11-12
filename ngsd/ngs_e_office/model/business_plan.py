from odoo import api, Command, fields, models, _
from collections import defaultdict
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval


class BusinessPlan(models.Model):
    _name = "business.plan"
    _description = "Kế hoạch công tác"
    _rec_name = "code"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    project_id = fields.Many2one("project.project", "Dự án")
    origin = fields.Char("Điểm xuất phát", required=True)
    location = fields.Char("Địa điểm công tác", required=True)
    responsible_id = fields.Many2one("hr.employee", "Người phụ trách", default=lambda self: self.env.user.employee_id)
    estimate_time_start = fields.Date("Ngày bắt đầu dự kiến", required=True)
    estimate_time_end = fields.Date("Ngày kết thúc dự kiến", required=True)
    code = fields.Char("Mã kế hoạch công tác")

    partner_ids = fields.One2many("business.plan.partner", "plan_id", "Nhân sự công tác")
    estimate_ids = fields.One2many("business.estimate_expense", 'plan_id', "Chi phí ước tính")

    state = fields.Selection([("new", "Mới"), ("waiting", "Chờ duyệt"), ("approved", "Đã duyệt"), ("denied", "Từ chối"), ("cancel", "Hủy")], default="new", string="Trạng thái")
    approver_ids = fields.One2many('approval.approver', 'business_plan_id', string="Approvers", readonly=1)
    is_next_user_to_approve = fields.Boolean(compute="_compute_is_next_user_in_approver_list", string="Is next user to approve")
    is_sale = fields.Boolean("Đi sale")

    show_button_request = fields.Boolean(compute="_compute_show_button")
    show_button_cancel = fields.Boolean(compute="_compute_show_button")
    show_btn_draft = fields.Boolean(compute="_compute_show_button")

    @api.depends_context('uid')
    @api.depends('state', 'responsible_id', 'approver_ids')
    def _compute_show_button(self):
        for record in self:
            record.show_button_request = record.state == 'new' and self.env.user.employee_id == record.responsible_id
            record.show_button_cancel = record.state not in ['cancel', 'denied', 'approved'] and self.env.user.employee_id == record.responsible_id
            record.show_btn_draft = (self.env.user.employee_id == record.responsible_id
                                     and record.state == 'waiting'
                                     and record.approver_ids[0].status == 'pending')

    def get_flow_domain(self):
        return [('model', '=', self._name), '|', ('block_ids', '=', False), ('block_ids', '=', self.sudo().responsible_id.en_block_id.id), '|',
                ('department_ids', '=', False), ('department_ids', '=', self.sudo().responsible_id.department_id.id), '|',
                ('en_department_ids', '=', False), ('en_department_ids', '=', self.sudo().responsible_id.en_department_id.id)]

    @api.depends('approver_ids')
    def _compute_is_next_user_in_approver_list(self):
        for record in self:
            next_approver = self.env["office.approve.flow"]._get_next_possible_approver(self.approver_ids)

            if not next_approver:
                record.is_next_user_to_approve = False
                continue
            if self.env.user == next_approver.user_id and next_approver.status == 'pending':
                record.is_next_user_to_approve = True
            else:
                record.is_next_user_to_approve = False

    def apply_approval_flow(self):
        self.ensure_one()
        request = self.sudo()
        processes = self.env['office.approve.flow'].search(self.get_flow_domain(), order='id desc')
        approver_id_vals = []
        for process in processes:
            if not request.filtered_domain(safe_eval(process.domain or '[]')):
                continue
            for rule in process.rule_ids.sorted(lambda x: x.visible_sequence):
                approver_user_id = self.env['res.users']
                role_selection = False
                if rule.type == 'person':
                    approver_user_id = rule.user_id
                    role_selection = rule.en_role_detail
                if rule.type == 'role' and rule.role_selection:
                    employee = request.responsible_id
                    role_selection_selection = dict(rule.fields_get(['role_selection'])['role_selection']['selection'])
                    if rule.role_selection == 'block':
                        approver_user_id = employee.en_block_id.en_project_implementation_id
                    if rule.role_selection == 'department':
                        approver_user_id = employee.department_id.manager_id.user_id
                    if rule.role_selection == 'en_department':
                        approver_user_id = employee.en_department_id.manager_id.user_id
                    if rule.role_selection == 'manager':
                        approver_user_id = employee.parent_id.user_id
                    if rule.role_selection == 'project_manager':
                        approver_user_id = request.project_id.en_project_manager_id
                    if rule.role_selection == 'pm_project':
                        approver_user_id = request.project_id.user_id
                    role_selection = role_selection_selection.get(rule.role_selection)
                if not approver_user_id:
                    continue
                approver_id_vals.append(Command.create({
                    'user_id': approver_user_id.id,
                    'status': 'pending',
                    'required': rule.required,
                    'role_selection': role_selection,
                }))
            break
        if not approver_id_vals:
            raise UserError('Không tìm thấy quy trình duyệt hoặc người duyệt tương ứng')
        approver_id_vals = [(5, 0, 0)] + approver_id_vals
        request.update({'approver_ids': approver_id_vals})

    def button_request(self):
        self.apply_approval_flow()
        current_approver = self.env["office.approve.flow"]._get_next_possible_approver(self.approver_ids)
        self._notify_users(current_approver.user_id, "Bạn có bản ghi Kế hoạch công tác cần phê duyệt. Vui lòng bấm tại đây để xem chi tiết.")
        self.write({
            "state": "waiting"
        })

    def button_draft(self):
        self.write({'approver_ids': False, "state": "new"})

    def _notify_users(self, users, message):
        action = self.env.ref("ngs_e_office.action_open_business_plan")
        access_link = f'/web#id={self.id}&action={action.id}&model=business.plan&view_type=form'
        self.sudo().send_notify(message, users, access_link=access_link)

    def button_confirm(self):
        current_approver = self.env["office.approve.flow"]._get_next_possible_approver(self.approver_ids)
        if current_approver == self.approver_ids[-1]:
            current_approver.write({
                'status': 'approved'
            })
            self.write({
                "state": "approved"
            })
            self._notify_users(self.sudo().responsible_id.user_id, "Bản ghi Kế hoạch công tác của bạn đã được phê duyệt. Vui lòng bấm tại đây để xem chi tiết.")
        else:
            current_approver.write({
                'status': 'approved'
            })
            self._notify_users(self.env["office.approve.flow"]._get_next_possible_approver(self.approver_ids).user_id, "Bạn có bản ghi Kế hoạch công tác cần phê duyệt. Vui lòng bấm tại đây để xem chi tiết.")

    def button_deny(self):
        current_approver = self.env["office.approve.flow"]._get_next_possible_approver(self.approver_ids)
        current_approver.write({
                'status': 'refused'
        })
        self.write({
            "state": "denied"
        })
        self._notify_users(self.sudo().responsible_id.user_id, "Bản ghi Kế hoạch của bạn đã bị từ chối. Vui lòng bấm vào đây để xem chi tiết.")

    def button_cancel(self):
        self.write({
            "state": "cancel"
        })

    @api.onchange('estimate_ids')
    def onchange_estimate_ids(self):
        sequence = 1
        for estimate in self.estimate_ids:
            estimate.sequence = sequence
            sequence += 1

    @api.model
    def create(self, values):
        pos_name = self.env['ir.sequence'].next_by_code('code.business.plan')
        values.update({
            "code": pos_name
        })
        return super().create(values)


class BusinessPlanPartner(models.Model):
    _name = "business.plan.partner"
    
    employee_id = fields.Many2one("hr.employee", "Tên người công tác", required=True)
    support_employee_id = fields.Many2one("hr.employee", "Người hỗ trợ trong thời gian công tác", required=True)
    department_id = fields.Many2one("hr.department", related="employee_id.department_id", string="Trung tâm/ban")
    employee_code = fields.Char("Mã nhân sự", related="employee_id.barcode")
    plan_id = fields.Many2one("business.plan", "Kế hoạch công tác")
    position = fields.Char("Vị trí", related="employee_id.job_title")


class BusinessEstimateExpense(models.Model):
    _name = "business.estimate_expense"
    sequence = fields.Integer("STT", default=1)
    norms_amount = fields.Integer("Số tiền định mức")
    total_amount = fields.Integer("Thành tiền", compute="_compute_total")
    note = fields.Text("Ghi chú")
    category = fields.Char(string="Danh mục")
    category_id = fields.Many2one("business.category", string="Categ")
    plan_id = fields.Many2one("business.plan", "Kế hoạch công tác")
    amount = fields.Integer("Số lượng")

    @api.depends('norms_amount', "amount")
    def _compute_total(self):
        for record in self:
            try:
                record.total_amount = record.norms_amount * record.amount
            except:
                record.total_amount = 0


class BusinessCategory(models.Model):
    _name = "business.category"

    name = fields.Char("Tên")
