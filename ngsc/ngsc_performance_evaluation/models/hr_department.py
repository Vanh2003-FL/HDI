from odoo import models, fields, api, _


class HrDepartment(models.Model):
    _inherit = "hr.department"

    activity_type = fields.Selection(string="Loại hoạt động", tracing=1,
                                     selection=[('delivery', 'Sản xuất'),
                                                ('support', 'Hỗ trợ'),
                                                ('sales', 'Kinh doanh')])
