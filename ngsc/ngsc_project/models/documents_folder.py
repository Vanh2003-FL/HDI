from odoo import models, fields, api, _


class DocumentsFolder(models.Model):
    _inherit = "documents.folder"

    role_write_ids = fields.Many2many(string='Vai trò Nhân sự được ghi')
    employee_write_ids = fields.Many2many(string='Nhân sự được ghi')
    role_read_ids = fields.Many2many(string='Vai trò Nhân sự được xem')
    employee_read_ids = fields.Many2many(string='Nhân sự được xem')

    employee_write_role_ids = fields.Many2many(string='Nhân sự ghi theo vai trò')
    employee_read_role_ids = fields.Many2many(string='Nhân sự xem theo vai trò')
    domain_role_ids = fields.Many2many(string='Vai trò được ghi domain')
    domain_employee_ids = fields.Many2many(string='Nhân sự được ghi domain')

    def init(self):
        records = self.env["documents.folder"].search([])
        records._compute_employee_write_role()
        records._compute_employee_read_role()


    def _compute_role_employee(self):
        for rec in self:
            employee_ids = rec.en_project_id.en_resource_project_ids.mapped("employee_id.id")
            role_ids = rec.en_project_id.en_resource_project_ids.mapped("role_ids.id")
            rec.domain_role_ids = [(6, 0, role_ids)]
            rec.domain_employee_ids = [(6, 0, employee_ids)]

    @api.depends('role_write_ids')
    def _compute_employee_write_role(self):
        for rec in self:
            employee_ids = rec.en_project_id.en_resource_project_ids.filtered(
                lambda x: bool(x.role_ids & rec.role_write_ids)).mapped("employee_id.id")
            rec.employee_write_role_ids = [(6, 0, employee_ids)]

    @api.depends('role_read_ids')
    def _compute_employee_read_role(self):
        for rec in self:
            employee_ids = rec.en_project_id.en_resource_project_ids.filtered(
                lambda x: bool(x.role_ids & rec.role_read_ids)).mapped("employee_id.id")
            rec.employee_read_role_ids = [(6, 0, employee_ids)]