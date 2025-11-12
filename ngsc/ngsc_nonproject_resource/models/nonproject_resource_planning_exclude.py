# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class NonprojectResourcePlanningExclude(models.Model):
    _name = "nonproject.resource.planning.exclude"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Danh sách loại trừ nguồn lực ngoài dự án"

    name = fields.Char(string="Danh sách loại trừ", default="Danh sách loại trừ")
    state_ids = fields.Many2many("hr.employee.state", "nonproject_state_rel", "exclude_id", "state_id",
                                 string="Loại nhân viên áp dụng", help="Để trống nếu không áp dụng")
    department_ids = fields.Many2many("hr.department", "nonproject_department_rel", "exclude_id", "department_id",
                                 string="Trung tâm loại trừ", help="Để trống nếu không áp dụng")
    exclude_employee_ids = fields.One2many("nonproject.resource.planning.exclude.detail", "exclude_id",
                                           string="Danh sách nhân sự loại trừ")
    note = fields.Text(string="Ghi chú")
    create_uid = fields.Many2one("res.users", string="Người tạo", default=lambda self: self.env.user, readonly=True)

    def action_add_exclude_employee(self):
        action = {
            "name": "Chọn danh sách nhân sự cần thêm",
            "context": {"default_exclude_id": self.id,
                        "exclude_employee_ids": self.exclude_employee_ids.mapped("employee_id.id")},
            "view_mode": "form",
            "res_model": "nonproject.resource.planning.wizard",
            'views': [(self.env.ref('ngsc_nonproject_resource.nonproject_resource_planning_wizard_add_view_form').id,
                       'form')],
            'type': 'ir.actions.act_window',
            'target': 'new',
        }
        return action

    def action_remove_exclude_employee(self):
        action = {
            "name": "Chọn danh sách nhân sự cần xóa",
            "context": {"default_exclude_id": self.id, "exclude_employee_ids": self.exclude_employee_ids.ids},
            "view_mode": "form",
            "res_model": "nonproject.resource.planning.wizard",
            'views': [(self.env.ref('ngsc_nonproject_resource.nonproject_resource_planning_wizard_remove_view_form').id,
                       'form')],
            'type': 'ir.actions.act_window',
            'target': 'new',
        }
        return action

    # Lấy danh sách nhân sự loại trừ nguồn lực ngoài dự án
    def get_nonproject_resource_planning_exclude_employee(self, date):
        Employee = self.env['hr.employee'].sudo()
        departments = self.env['hr.department']
        all_exclude_ids = set()
        for rec in self.sudo().search([]):
            departments += rec.department_ids
            domain = []
            if rec.exclude_employee_ids:
                employee_ids = rec.exclude_employee_ids.filtered(lambda l: l.employee_id and (
                        (l.date_from_convert and l.date_to_convert and l.date_from_convert <= date <= l.date_to_convert) or
                        (l.date_from_convert and not l.date_to_convert and date >= l.date_from_convert) or
                        (not l.date_from_convert and l.date_to_convert and date <= l.date_to_convert) or
                        (not l.date_from_convert and not l.date_to_convert))).mapped('employee_id.id')
                domain.append(('id', 'in', employee_ids))
            if rec.state_ids:
                domain.append(('state_hr_employee', 'in', rec.state_ids.mapped('code')))
            if rec.department_ids:
                domain.append(('department_id', 'in', rec.department_ids.ids))
            if domain:
                if len(domain) > 1:
                    domain = ['|'] * (len(domain) - 1) + domain
                exclude_ids = Employee.search(domain)
                all_exclude_ids.update(exclude_ids.ids)
        return Employee.browse(list(all_exclude_ids)), departments


class NonprojectResourcePlanningExcludeDetail(models.Model):
    _name = "nonproject.resource.planning.exclude.detail"
    _rec_name = "employee_id"
    _description = "Danh sách loại trừ nguồn lực ngoài dự án chi tiết"

    exclude_id = fields.Many2one("nonproject.resource.planning.exclude", string="Loại trừ", ondelete="cascade")
    employee_id = fields.Many2one("hr.employee", string="Nhân viên", required=True)
    en_type_id = fields.Many2one("en.type", string="Loại", related="employee_id.en_type_id", readonly=True)
    state_hr_employee = fields.Selection(string="Tình trạng", related="employee_id.state_hr_employee",
                                         selection=[('permanent', 'Chính thức'),
                                                    ('probation', 'Thử việc'),
                                                    ('training', 'Đào tạo'),
                                                    ('inter', 'Thực tập'),
                                                    ('maternity', 'Thai sản'),
                                                    ('semi-inactive', 'Nghỉ không lương'),
                                                    ('contract_lease', 'Thuê khoán')], readonly=True)
    barcode = fields.Char(string="Mã nhân sự", related="employee_id.barcode", readonly=True)
    job_title = fields.Char(string="Chức danh", related="employee_id.job_title", readonly=True)
    work_email = fields.Char(string="Email", related="employee_id.work_email", readonly=True)
    en_area_id = fields.Many2one("en.name.area", string="Khu vực", related="employee_id.en_area_id", readonly=True)
    en_block_id = fields.Many2one("en.name.block", string="Khối", related="employee_id.en_block_id", readonly=True)
    department_id = fields.Many2one("hr.department", string="Trung tâm/Ban", related="employee_id.department_id",
                                    readonly=True)
    en_department_id = fields.Many2one("en.department", string="Phòng", related="employee_id.en_department_id",
                                       readonly=True)
    en_status_hr = fields.Selection(string="Trạng thái", related="employee_id.en_status_hr",
                                    selection=[('active', 'Hoạt động'),
                                               ('inactive', 'Nghỉ việc'),
                                               ('semi-inactive', 'Nghỉ không lương'),
                                               ('maternity-leave', 'Nghỉ thai sản')], readonly=True)
    date_from = fields.Date(string="Thời gian bắt đấu")
    date_to = fields.Date(string="Thời gian kết thúc")
    date_from_convert = fields.Date(compute="_compute_date_from_convert", store=True)
    date_to_convert = fields.Date(compute="_compute_date_from_convert", store=True)

    @api.depends("date_from", "date_to")
    def _compute_date_from_convert(self):
        for rec in self:
            rec.date_from_convert = rec.date_from + relativedelta(day=1) if rec.date_from else False
            rec.date_to_convert = rec.date_to + relativedelta(day=1, months=1, days=-1) if rec.date_to else False

    @api.constrains("date_from", "date_to")
    def _constrains_date_from_date_to(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_from > rec.date_to:
                raise ValidationError("Thời gian bắt đầu không được lớn hơn Thời gian kết thúc.")

    @api.constrains("employee_id")
    def _constrains_employee_id(self):
        for rec in self:
            _domain = [("exclude_id", "=", rec.exclude_id.id),
                       ("employee_id", "=", rec.employee_id.id),
                       ("id", "!=", rec.id)]
            if self.search(_domain):
                raise ValidationError(f"Nhân viên {rec.employee_id.name} đã có trong danh sách loại trừ.")
