from odoo import models, fields, api, _
from odoo.tools.safe_eval import safe_eval
from odoo.tools.misc import clean_context


class OfficeApproveFlow(models.Model):
    _name = "office.approve.flow"
    _description = "Quy trình phê duyệt"

    name = fields.Char(string="Tên quy trình", required=True)
    block_ids = fields.Many2many(comodel_name="en.name.block", string="Khối áp dụng")
    department_ids = fields.Many2many(comodel_name="hr.department", string="Trung tâm/Ban áp dụng")
    en_department_ids = fields.Many2many(comodel_name="en.department", string="Phòng áp dụng")
    model_id = fields.Many2one(comodel_name='ir.model', string='Loại chứng từ', required=True, ondelete='cascade')
    model = fields.Char(related='model_id.model', store=True)
    domain = fields.Char(string="Điều kiện")
    rule_ids = fields.One2many(comodel_name="office.approve.rule", inverse_name="flow_id", string="Quy tắc phê duyệt")

    @api.depends("rule_ids")
    def _compute_max_line_sequence(self):
        for rec in self:
            rec.max_line_sequence = max(rec.mapped("rule_ids.sequence") or [0]) + 1

    max_line_sequence = fields.Integer(string="Max sequence in lines", compute="_compute_max_line_sequence", store=True)

    def _get_next_possible_approver(self, approver_ids, exclude_state = ['approved']):
        for approver in approver_ids.sorted('sequence'):
            if approver.status in exclude_state:
                continue
            else:
                return approver
        return self.env["approval.approver"]

class OfficeApproveRule(models.Model):
    _name = "office.approve.rule"
    _description = "Quy tắc phê duyệt"

    en_role_detail = fields.Char(string='Vai trò/Vị trí')

    flow_id = fields.Many2one(comodel_name="office.approve.flow", string="Vai trò", required=True, ondelete='cascade')
    sequence = fields.Integer(help="Gives the sequence of this line when displaying.", default=9999)

    visible_sequence = fields.Integer("Trình tự", help="Displays the sequence of the line.", compute="_compute_visible_sequence", store=True, )

    @api.depends("sequence", "flow_id.rule_ids")
    def _compute_visible_sequence(self):
        for so in self.mapped("flow_id"):
            sequence = 1
            order_lines = so.rule_ids
            for line in sorted(order_lines, key=lambda l: l.sequence):
                line.visible_sequence = sequence
                sequence += 1

    type = fields.Selection([('role', "Vai trò"), ('person', "Người chỉ định")], string="Loại người duyệt")
    role_id = fields.Many2one(comodel_name="en.approve.role", string="Vai trò phê duyệt")
    role_selection = fields.Selection(selection=[
        ('block', 'Giám đốc Khối'),
        ('department', 'Giám đốc Trung tâm/Ban'),
        ('en_department', 'Trưởng phòng'),
        ('manager', 'Người quản lý'),
        ('project_manager', 'Giám đốc dự án'),
        ('pm_project', 'PM dự án')
        ], string="Vai trò phê duyệt")
    user_id = fields.Many2one(comodel_name="res.users", string="Người phê duyệt")
    required = fields.Boolean(default=True)


class ApprovalApprover(models.Model):
    _inherit = "approval.approver"

    role_selection = fields.Char(string="Vai trò")
    business_plan_id = fields.Many2one("business.plan", "Kế hoạch công tác")
