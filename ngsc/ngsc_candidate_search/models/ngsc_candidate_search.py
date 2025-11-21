# -*- coding: utf-8 -*-
from odoo import models, fields, api, _, exceptions
from odoo.exceptions import ValidationError


class NgscCandidateSearch(models.Model):
    _name = "ngsc.candidate.search"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "id desc"
    _description = "Tìm kiếm nguồn lực nhân sự"

    name = fields.Char(string="Tên bản ghi tìm kiếm", required=False, tracking=True)
    search_history_id = fields.Many2one("ngsc.candidate.search", string="Tìm kiếm đã lưu", tracking=True)
    en_area_id = fields.Many2one("en.name.area", string="Chi nhánh", tracking=True)
    en_block_id = fields.Many2one("en.name.block", string="Khối", tracking=True)
    hr_department_id = fields.Many2one("hr.department", string="Trung tâm/Ban", tracking=True)
    en_department_id = fields.Many2one("en.department", string="Phòng", tracking=True)
    job_id = fields.Many2one("hr.job", string="Vị trí công việc", tracking=True)
    contract_type_id = fields.Many2one("hr.contract.type", string="Loại hợp đồng", tracking=True)
    hr_employee_id = fields.Many2one("hr.employee", string="Họ và tên", tracking=True)
    skill_ids = fields.Many2many("ngsc.competency.skill", "candidate_search_competency_skill_rel",
                                 "candidate_search_id", "competency_skill_id", string="Kỹ năng")
    line_ids = fields.One2many("ngsc.candidate.search.line", "candidate_search_id",
                               string="Tham số kỹ năng tìm kiếm nhân sự")
    flag_save_data = fields.Boolean(string="Cờ lưu thông tin")
    score_total = fields.Float(string="Tổng điểm kỹ năng", compute="_compute_score_total", store=True)

    def do_search(self):
        # if not self.line_ids:
        #     raise ValidationError("Yêu cầu nhập thông tin kỹ năng tìm kiếm.")

        is_save = self.env.context.get('isSave', False)
        # Kiểm tra nếu flag_save_data = True và trường name trống
        if is_save:
            if not self.name:
                raise ValidationError("Trường 'Tên bản ghi tìm kiếm' không được để trống khi lưu dữ liệu.")
            save_search = {}
            # Sao chép các dòng con
            save_line_ids = []
            for line in self.line_ids:
                save_line_ids.append((0, 0, {
                    'skill_id': line.skill_id.id,
                    'level_id': line.level_id.id,
                    'priority': line.priority,
                    'weight': line.weight,
                }))

            save_search['line_ids'] = save_line_ids
            save_search['flag_save_data'] = True
            super(NgscCandidateSearch, self).copy(save_search)

        total = sum(line.weight for line in self.line_ids)
        if total < 100 and self.line_ids:
            raise ValidationError("Tổng trọng số thấp hơn 100%. Yêu cầu nhập lại.")

        self.env['ngsc.candidate.search.result'].filter_data(search_info_id=self)

        # Trả về hành động với thông tin cần thiết
        return {
            'type': 'ir.actions.act_window',
            'name': 'Danh sách nhân viên',  # Tên của cửa sổ hành động
            'res_model': 'ngsc.candidate.search.result',
            'view_mode': 'tree',
            'views': [[False, 'tree']],
            'view_id': self.env.ref('ngsc_candidate_search.view_candidate_search_result_tree').id,
            'target': 'main',
            'domain': [('candidate_search_id', '=', self.id)],
            'context': {
                'reload': True,
                'candidate_search_id': self.id,
                'show_export_candidate_search_button': True,
            }
        }

    def _update_skill_lines(self):
        for record in self:
            # Lấy danh sách các kỹ năng đã chọn từ skill_ids
            selected_skills = record.skill_ids

            existing_lines = {line.skill_id.id: line for line in record.line_ids}
            line_data = []
            existing_skill_id = list(existing_lines.keys())

            # Duyệt các kỹ năng mới
            for skill in selected_skills:
                if skill.id.origin in existing_skill_id:
                    line = existing_lines[skill.id.origin]
                    line_data.append((0, 0, {
                        'skill_id': line.skill_id,
                        'weight': line.weight,
                        'level_id': line.level_id,
                        'candidate_search_id': line.candidate_search_id,
                        'priority': line.priority,
                        'skill_group_id': line.skill_group_id
                    }))
                else:
                    # Tạo dòng mới cho kỹ năng chưa có
                    line_data.append((0, 0, {
                        'skill_id': skill.id
                    }))

            # Cập nhật line_ids với dữ liệu mới
            self.line_ids = [(5, 0, 0)] + line_data

    @api.onchange('skill_ids')
    def _onchange_skill_ids(self):
        # Khi skill_ids thay đổi, gọi phương thức _update_skill_lines
        self._update_skill_lines()

    @api.onchange('line_ids')
    def _onchange_line_ids(self):
        # Kiểm tra khi có sự thay đổi trong line_ids
        if not self.line_ids:
            # Nếu không còn dòng nào trong line_ids, có thể cập nhật lại skill_ids (ví dụ: xóa hết kỹ năng)
            self.skill_ids = [(5, 0, 0)]  # Xóa tất cả các giá trị trong skill_ids
        else:
            # Nếu có dòng trong line_ids, có thể cập nhật lại skill_ids theo cách khác
            skills = self.line_ids.mapped('skill_id')
            self.skill_ids = [(6, 0, skills.ids)]  # Cập nhật lại skill_ids với các kỹ năng đã chọn

        total = sum(line.weight for line in self.line_ids)
        if total > 100:
            raise ValidationError("Tổng trọng số vượt 100%. Yêu cầu nhập lại.")

    @api.onchange('search_history_id')
    def _onchange_search_history_id(self):
        if self.search_history_id:
            history = self.search_history_id
            # Gán các trường đơn
            self.en_area_id = history.en_area_id.id
            self.en_block_id = history.en_block_id.id
            self.hr_department_id = history.hr_department_id.id
            self.en_department_id = history.en_department_id.id
            self.job_id = history.job_id.id
            self.contract_type_id = history.contract_type_id.id
            self.hr_employee_id = history.hr_employee_id.id
            self.skill_ids = [(6, 0, history.skill_ids.ids)]
            # Gán lại giá trị các trường từ bản ghi lịch sử đã lưu
            self.name = history.name
            line_ids = [(5, 0, 0)]
            for line in history.line_ids:
                line_ids += [(0, 0, {
                    'skill_id': line.skill_id.id,
                    'level_id': line.level_id.id,
                    'priority': line.priority,
                    'weight': line.weight,
                })]
            self.line_ids = line_ids

    @api.model
    def open_recent(self, old_id):
        old_record = self.browse(old_id)
        if old_record.exists():
            return {
                'type': 'ir.actions.act_window',
                'name': 'Tìm kiếm nguồn lực nhân sự',
                'res_model': 'ngsc.candidate.search',
                'views': [[self.env.ref('ngsc_candidate_search.ngsc_candidate_search_wizard_form').id, 'form']],
                'context': {},
                'res_id': old_record.id,
                'target': 'new'
            }

    @api.depends('line_ids.score', 'line_ids.score')
    def _compute_score_total(self):
        for rec in self:
            rec.score_total = sum(rec.line_ids.mapped('score'))
