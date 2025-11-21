# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _, exceptions
from odoo.exceptions import ValidationError


class HrPerformanceEvaluationExclude(models.Model):
    _name = "ngsc.hr.performance.evaluation.exclude"
    _description = "Danh sách loại trừ đánh giá hiệu suất"

    name = fields.Char(string="Danh sách loại trừ", default="Danh sách loại trừ")
    state_ids = fields.Many2many("hr.employee.state", "performance_evaluation_hr_state_rel", "exclude_id", "state_id",
                                 string="Loại nhân viên áp dụng", help="Để trống nếu không áp dụng")
    block_ids = fields.Many2many("en.name.block", "performance_evaluation_hr_block_rel", "exclude_id", "block_id",
                                 string="Khối áp dụng", help="Để trống nếu không áp dụng")
    exclude_employee_ids = fields.One2many("ngsc.hr.performance.evaluation.exclude.detail", "exclude_id",
                                           string="Danh sách nhân sự loại trừ")
    available_employee_ids = fields.Many2many("hr.employee", "performance_evaluation_available_employee_rel",
                                              "exclude_id", "employee_id", string="Danh sách nhân sự khả dụng",
                                              compute="_compute_available_employee_ids")
    note = fields.Text(string="Ghi chú")
    create_uid = fields.Many2one("res.users", string="Approved by", default=lambda self: self.env.user, readonly=True)

    @api.depends("state_ids", "block_ids")
    def _compute_available_employee_ids(self):
        for rec in self:
            _domain = [('en_internal_ok', '=', True)]
            if rec.state_ids:
                _domain.append(('state_hr_employee', 'in', rec.state_ids.mapped('code')))
            if rec.block_ids:
                _domain.append(('en_block_id', 'in', rec.block_ids.ids))
            rec.available_employee_ids = [(6, 0, self.env['hr.employee'].sudo().search(_domain).ids)]

    def action_add_exclude_employee(self):
        action = {
            "name": "Chọn danh sách nhân sự cần thêm",
            "context": {"default_exclude_id": self.id,
                        "add_employee_ids": self.available_employee_ids.ids,
                        "exclude_employee_ids": self.exclude_employee_ids.mapped("employee_id.id")},
            "view_mode": "form",
            "res_model": "performance.evaluation.exclude.wizard",
            'views': [(self.env.ref('ngsc_performance_evaluation.performance_evaluation_add_wizard_view_form').id,
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
            "res_model": "performance.evaluation.exclude.wizard",
            'views': [(self.env.ref('ngsc_performance_evaluation.performance_evaluation_exclude_wizard_view_form').id,
                       'form')],
            'type': 'ir.actions.act_window',
            'target': 'new',
        }
        return action

    # Lấy danh sách nhân sự loại trừ đánh giá hiệu suất
    def get_performance_evaluation_exclude_employee(self, date):
        Employee = self.env['hr.employee'].sudo()
        all_exclude_ids = set()
        # Loại trừ phòng ban loại hoạt động kinh doanh
        ex_employee_ids = self.env["hr.employee"].search(['|', ('department_id.activity_type', '=', False),
                                                          ('department_id.activity_type', '=', 'sales')])
        if ex_employee_ids:
            all_exclude_ids.update(ex_employee_ids.ids)
        for rec in self.sudo().search([]):
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
            if rec.block_ids:
                domain.append(('en_block_id', 'in', rec.block_ids.ids))
            if domain:
                exclude_ids = Employee.search(domain).ids
                all_exclude_ids.update(exclude_ids)
        return list(all_exclude_ids)

    def action_import_exclude_employee(self):
        action = self.env['ir.actions.client']._for_xml_id('ngsc_performance_evaluation.exclude_employee_import_client')
        action['params']['res_id'] = self.id
        return action


class HrPerformanceEvaluationExcludeDetail(models.Model):
    _name = "ngsc.hr.performance.evaluation.exclude.detail"
    _rec_name = "employee_id"
    _description = "Danh sách loại trừ đánh giá hiệu suất chi tiết"

    exclude_id = fields.Many2one("ngsc.hr.performance.evaluation.exclude", string="Loại trừ", ondelete="cascade")
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
    work_email = fields.Char(string="Email")
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

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        self.work_email = self.employee_id.work_email

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

    @api.model
    def create(self, vals):
        if self._context.get("import_file", False):
            if 'employee_id' in vals:
                vals.pop('employee_id', None)
            if 'work_email' in vals:
                work_email = vals.get('work_email')
                employee = self.env['hr.employee'].sudo().search([('work_email', '=', work_email)], limit=1)
                if employee:
                    vals['employee_id'] = employee.id
        res = super().create(vals)
        if not res.employee_id and self._context.get("import_file", False):
            raise ValueError("Không tìm thấy nhân sự với email: {}".format(work_email))
        return res
