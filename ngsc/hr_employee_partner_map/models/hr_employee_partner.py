from odoo import models, fields, api, _


class HrEmployeePartner(models.Model):
    _name = 'hr.employee.partner'
    _description = 'Mapping Employee <-> Partner'

    employee_id = fields.Many2one('hr.employee', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', required=True, ondelete='cascade')

    _sql_constraints = [
        ('unique_employee_partner', 'unique(employee_id, partner_id)', 'Mapping must be unique!'),
    ]

    @api.model
    def sync_employee_partner(self):
        """Sync all employees to mapping table and create res.partner if not exist"""
        employees = self.env['hr.employee'].sudo().search([])
        for emp in employees:
            # Lấy partner của employee
            partner = emp.user_id.partner_id or emp.address_home_id
            if not partner:
                # Nếu employee chưa có partner, tạo mới
                partner = self.env['res.partner'].sudo().create({
                    'name': emp.name,
                })
            # Tạo mapping nếu chưa có
            self.get_or_create(emp, partner)

    @api.model
    def get_or_create(self, employee, partner):
        rec = self.search([('employee_id', '=', employee.id), ('partner_id', '=', partner.id)], limit=1)
        if not rec:
            rec = self.create({'employee_id': employee.id, 'partner_id': partner.id})
        return rec
