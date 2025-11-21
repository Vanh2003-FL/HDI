from odoo import models, fields, api, _


class RecruitmentCouncil(models.Model):
    _name = 'ngsc.recruitment.council'
    _description = 'Hội đồng tuyển dụng'

    emp_id = fields.Many2one('hr.employee', string='Nhân sự')
    department = fields.Char(string='Trung tâm/Ban', readonly=True, store=True)
    email = fields.Char(string='Email', readonly=True, store=True)
    role = fields.Char(string='Chức vụ', readonly=True, store=True)
    plan_id = fields.Many2one('ngsc.recruitment.plan', "Kế hoạch tuyển dụng")

    stt = fields.Integer(string="STT", compute="_compute_stt", store=False)

    @api.depends('plan_id.council_ids')
    def _compute_stt(self):
        for rec in self:
            if rec.plan_id:
                # Lấy danh sách và enumerate luôn
                for index, council in enumerate(rec.plan_id.council_ids, start=1):
                    if council == rec:  # So sánh object thay vì id
                        rec.stt = index
                        break
            else:
                rec.stt = 0  # Chưa có plan thì để 0 hoặc rỗng

    @api.onchange('emp_id')
    def _onchange_emp_id(self):
        if self.emp_id:
            self.department = self.emp_id.department_id.name or ''
            self.email = self.emp_id.work_email or ''
            self.role = self.emp_id.job_id.name or ''
        else:
            self.department = ''
            self.email = ''
            self.role = ''

