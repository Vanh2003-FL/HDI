from odoo import models, fields, api, _


class EmployeeDepartmentBorrowWizard(models.TransientModel):
    _name = "emp.department.borrow.wizard"
    _description = "Tìm kiếm danh sách nhân sự trong dự án của trung tâm khác"

    department_ids = fields.Many2many('hr.department', 'emp_borrow_department_prj_ref',  string='Trung tâm của dự án')
    project_ids = fields.Many2many('project.project', string='Dự án')

    department_emp_ids = fields.Many2many('hr.department', 'emp_borrow_department_emp_ref', string='Trung tâm của nhân sự')
    emp_ids = fields.Many2many('hr.employee', string='Nhân viên')

    @api.onchange('department_ids')
    def _onchange_department_ids(self):
        if not self:
            return
        # clear selection
        self.project_ids = [(5, 0, 0)]
        # set domain: nếu có chọn department_ids -> lọc theo chúng, ngược lại -> không lọc
        domain = [('en_department_id', 'in', self.department_ids.ids)] if self.department_ids else []
        return {'domain': {'project_ids': domain}}

    @api.onchange('department_emp_ids')
    def _onchange_department_emp_ids(self):
        if not self:
            return
        self.emp_ids = [(5, 0, 0)]
        domain = [('department_id', 'in', self.department_emp_ids.ids)] if self.department_emp_ids else []
        return {'domain': {'emp_ids': domain}}

    def do(self):
        self = self.sudo()
        action = self.env.ref('account_reports.action_employee_department_borrow').read()[0]
        action['target'] = 'main'
        action['context'] = {'model': 'employee.department.borrow',
                             'project_ids': self.project_ids.ids,
                             'department_ids': self.department_ids.ids,
                             'emp_ids': self.emp_ids.ids,
                             'department_emp_ids': self.department_emp_ids.ids,
                             'id_popup': self.id}
        return action

