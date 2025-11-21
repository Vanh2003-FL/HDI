from odoo import models, fields, api, _


class HrRecruitmentStage(models.Model):
    _inherit = "hr.recruitment.stage"

    state_type = fields.Selection(string="Loại giai đoạn", tracking=True,
                                  selection=[("send_applications", "Ứng viên gửi hồ sơ"),
                                             ("receive_applications", "Nhận hồ sơ"),
                                             ("appraisal", "Thẩm định ban đầu"),
                                             ("interview", "Phỏng vấn"),
                                             ("contract_proposal", "Đề xuất hợp đồng"),
                                             ("contract_signed", "Hợp đồng đã ký")])
