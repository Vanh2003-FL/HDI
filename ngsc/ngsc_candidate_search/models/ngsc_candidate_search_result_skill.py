from odoo import models, fields, _


class NGSCCandidateSearchResultSkill(models.TransientModel):
    _name = "ngsc.candidate.search.result.skill"
    _description = "Kỹ năng của kết quả tìm kiếm nguồn lực nhân sự"

    candidate_search_result_id = fields.Many2one(
        "ngsc.candidate.search.result",
        string="Kết quả tìm kiếm",
        required=True,
        ondelete="cascade"  # Xóa skill nếu bản ghi kết quả tìm kiếm bị xóa
    )
    hr_employee_id = fields.Many2one(
        "hr.employee",
        string="Nhân sự",
        store=True
    )
    emp_skill_id = fields.Many2one(
        "hr.employee.skills",
        string="Kỹ năng",
        store=True
    )
    score = fields.Float(string="Điểm số")

