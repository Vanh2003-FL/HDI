# -*- coding: utf-8 -*-
import urllib

import base64
import io

import xlsxwriter

from odoo import models, fields, api


class NgscCandidateSearchResult(models.TransientModel):
    _name = "ngsc.candidate.search.result"
    _description = "Kết quả tìm kiếm nguồn lực nhân sự"

    candidate_search_id = fields.Many2one("ngsc.candidate.search", string="Tìm kiếm nguồn lực nhân sự")
    hr_employee_id = fields.Many2one("hr.employee", string="Tên nhân sự")
    en_type_id = fields.Many2one("en.type", string="Loại")
    barcode = fields.Char(string="Mã nhân sự")
    job_title = fields.Char(string="Chức danh")
    work_email = fields.Char(string="Email")
    en_area_id = fields.Many2one("en.name.area", string="Khu vực")
    en_block_id = fields.Many2one("en.name.block", string="Khối")
    department_id = fields.Many2one("hr.department", string="Trung tâm/Ban")
    en_department_id = fields.Many2one("en.department", string="Phòng")
    weight = fields.Integer(string="Trọng số (%)", default=0)
    state_hr_employee = fields.Selection(string="Tình trạng",
                                         selection=[('permanent', 'Chính thức'),
                                                    ('probation', 'Thử việc'),
                                                    ('training', 'Đào tạo'),
                                                    ('inter', 'Thực tập'),
                                                    ('maternity','Thai sản'),
                                                    ('semi-inactive', 'Nghỉ không lương'),
                                                    ('contract_lease', 'Thuê khoán')])
    en_status_hr = fields.Selection(string="Trạng thái",
                                    selection=[('active', 'Hoạt động'),
                                               ('inactive', 'Nghỉ việc'),
                                               ('semi-inactive', 'Nghỉ không lương'),
                                               ('maternity-leave', 'Nghỉ thai sản')])
    skill_ids = fields.One2many(
        "ngsc.candidate.search.result.skill",
        "candidate_search_result_id",
        string="Danh sách kỹ năng"
    )

    @staticmethod
    def _build_where_clauses_query(search_info_id):
        where_clauses = ["he.active = TRUE", "he.en_status_hr = 'active'"]
        values = []
        if search_info_id.en_area_id:
            where_clauses.append("he.en_area_id = %s")
            values.append(search_info_id.en_area_id.id)
        if search_info_id.en_block_id:
            where_clauses.append("he.en_block_id = %s")
            values.append(search_info_id.en_block_id.id)
        if search_info_id.hr_department_id:
            where_clauses.append("he.department_id = %s")
            values.append(search_info_id.hr_department_id.id)
        if search_info_id.en_department_id:
            where_clauses.append("he.en_department_id = %s")
            values.append(search_info_id.en_department_id.id)
        if search_info_id.job_id:
            where_clauses.append("he.job_id = %s")
            values.append(search_info_id.job_id.id)
        if search_info_id.contract_type_id:
            where_clauses.append("he.contract_type_id = %s")
            values.append(search_info_id.contract_type_id.id)
        if search_info_id.hr_employee_id:
            where_clauses.append("he.id = %s")
            values.append(search_info_id.hr_employee_id.id)
        if search_info_id.line_ids:
            skill_required = search_info_id.line_ids.filtered(lambda x: x.priority)
            if skill_required:
                skills = skill_required.mapped('skill_id.id')
            else:
                skills = search_info_id.line_ids.mapped('skill_id.id')
            if skills:
                where_clauses.append("hes.skill_id = ANY(%s)")
                values.append(skills)
        where_sql = " AND ".join(where_clauses)
        return where_sql, values

    def filter_data(self, search_info_id):
        uid = self.env.user.id
        self.env.cr.execute("""DELETE FROM ngsc_candidate_search_result WHERE create_uid = %s;""", (uid,))
        where_sql, values = self._build_where_clauses_query(search_info_id)
        insert_sql = f"""
            WITH filtered_employees AS (
                SELECT DISTINCT he.id AS hr_employee_id,
                                he.en_type_id,he.barcode, he.job_title, he.work_email,
                                he.en_area_id, he.en_block_id,
                                he.department_id, he.en_department_id,
                                he.state_hr_employee, he.en_status_hr
                FROM hr_employee he
                {'LEFT JOIN hr_employee_skills hes ON he.id = hes.hr_employee_id' if where_sql else ''}
                WHERE {where_sql}),
            scores AS (
                SELECT hes.hr_employee_id,
                       ROUND(SUM(hes.sequence * ncsl.weight)::numeric / %s, 0) AS score,
                       MAX(CASE WHEN ncsl.priority THEN 1 ELSE 0 END) AS has_priority_skill
                FROM hr_employee_skills hes
                INNER JOIN ngsc_candidate_search_line ncsl ON hes.skill_id = ncsl.skill_id
                WHERE ncsl.candidate_search_id = %s
                GROUP BY hes.hr_employee_id )
            INSERT INTO ngsc_candidate_search_result (
                create_uid, create_date, write_uid, write_date,
                candidate_search_id, hr_employee_id, en_type_id, barcode, job_title, work_email,
                en_area_id, en_block_id, department_id, en_department_id,
                state_hr_employee, en_status_hr, weight)
            SELECT %s, now(), %s, now(), %s,
                   fe.hr_employee_id, fe.en_type_id, fe.barcode, fe.job_title, fe.work_email,
                   fe.en_area_id, fe.en_block_id, fe.department_id, fe.en_department_id,
                   fe.state_hr_employee, fe.en_status_hr, sc.score
            FROM filtered_employees fe
            LEFT JOIN scores sc ON fe.hr_employee_id = sc.hr_employee_id
            ORDER BY sc.has_priority_skill DESC, sc.score DESC
            RETURNING id, hr_employee_id
        """
        final_params = values + [round(search_info_id.score_total, 2), search_info_id.id, uid, uid,search_info_id.id]

        try:
            self.env.cr.execute(insert_sql, final_params)
            if self.env.cr.rowcount == 0:
                return
            # Lấy danh sách id và hr_employee_id từ ngsc_candidate_search_result
            result_ids = self.env.cr.fetchall()  # Lấy các cặp (id, hr_employee_id)
            if result_ids:
                insert_skill_score_sql = """
                    INSERT INTO ngsc_candidate_search_result_skill (
                        candidate_search_result_id, hr_employee_id, emp_skill_id, score,
                        create_uid, create_date, write_uid, write_date
                    )
                    SELECT 
                        %s, ncsr.hr_employee_id, hes.id,
                        COALESCE(
                            ROUND((hes.sequence * ncsl.weight)::numeric / %s, 2),
                            0
                        ) AS score,
                        %s, now(), %s, now()
                    FROM hr_employee_skills hes
                    INNER JOIN ngsc_candidate_search_result ncsr ON hes.hr_employee_id = ncsr.hr_employee_id
                    LEFT JOIN ngsc_candidate_search_line ncsl 
                        ON hes.skill_id = ncsl.skill_id 
                        AND ncsl.candidate_search_id = %s
                    WHERE ncsr.id = %s
                """

                for result_id, hr_employee_id in result_ids:
                    skill_score_params = [
                        result_id,  # candidate_search_result_id
                        round(search_info_id.score_total, 2),  # Tổng điểm để chuẩn hóa
                        uid, uid,  # create_uid, write_uid
                        search_info_id.id,  # candidate_search_id cho ncsl
                        result_id  # ncsr.id để liên kết
                    ]
                    self.env.cr.execute(insert_skill_score_sql, skill_score_params)
        except Exception as e:
            print(e)

    #Export excel
    def action_export_excel(self):
        # Tạo workbook và worksheet
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet()

        # Danh sách trường nhân viên
        fields_to_export = [
            'hr_employee_id',
            'en_type_id',
            'barcode',
            'job_title',
            'work_email',
            'en_area_id',
            'en_block_id',
            'department_id',
            'en_department_id',
            'weight',
            'state_hr_employee',
            'en_status_hr'
        ]

        # Định dạng
        light_border = {'border': 1, 'border_color': '#D9D9D9'}
        header_format = workbook.add_format({'bold': True, 'bg_color': '#EEEEEE', **light_border})
        red_format = workbook.add_format({'bg_color': '#ffcccc', **light_border})
        yellow_format = workbook.add_format({'bg_color': '#ffffcc', **light_border})
        green_format = workbook.add_format({'bg_color': '#ccffcc', **light_border})
        cell_format = workbook.add_format(light_border)

        # Header: Thêm cột Nhóm kỹ năng, Thẻ, Kỹ năng, Mức độ hiện tại, Số điểm
        headers = [self._fields[field].string for field in fields_to_export] + [
            'Nhóm kỹ năng', 'Thẻ','Kỹ năng', 'Mức độ hiện tại', 'Số điểm'
        ]
        max_col_widths = [len(h) for h in headers]

        # Ghi header
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)

        # Lấy dữ liệu từ model
        records = self
        current_row = 1  # Bắt đầu từ dòng 1 (sau header)

        for record in records:
            # Sắp xếp skill_ids theo score giảm dần
            sorted_skills = sorted(record.skill_ids, key=lambda x: x.score or 0, reverse=True)
            skill_count = len(sorted_skills) or 1  # Ít nhất 1 dòng nếu không có kỹ năng
            start_row = current_row

            # Duyệt qua sorted_skills hoặc tạo dòng rỗng nếu không có kỹ năng
            skills = sorted_skills if sorted_skills else [None]
            cell_values = {}  # Lưu giá trị nhân viên để merge

            # Duyệt qua skills để ghi cột kỹ năng
            for skill in skills:
                # Ghi các cột nhân viên trước
                for col, field_name in enumerate(fields_to_export):
                    field = self._fields[field_name]
                    value = getattr(record, field_name)

                    if isinstance(field, fields.Many2one):
                        cell_value = value.name if value else ''
                    elif isinstance(field, fields.Many2many):
                        cell_value = ', '.join(value.mapped('name')) if value else ''
                    elif isinstance(field, (fields.Char, fields.Text)):
                        cell_value = value or ''
                    elif isinstance(field, fields.Boolean):
                        cell_value = 'Có' if value else 'Không'
                    elif isinstance(field, fields.Date):
                        cell_value = value.strftime('%d/%m/%Y') if value else ''
                    elif isinstance(field, fields.Selection):
                        cell_value = dict(field.selection).get(value)
                    else:
                        cell_value = value

                    cell_str = str(cell_value) if cell_value is not None else ''
                    if len(cell_str) > max_col_widths[col]:
                        max_col_widths[col] = len(cell_str)

                    # Lưu giá trị để merge
                    cell_values[field_name] = cell_value

                    # Ghi giá trị cho cột weight với định dạng màu
                    if field_name == 'weight':
                        if value is not None:
                            if value < 50:
                                worksheet.write(current_row, col, value, red_format)
                            elif value < 70:
                                worksheet.write(current_row, col, value, yellow_format)
                            else:
                                worksheet.write(current_row, col, value, green_format)
                        else:
                            worksheet.write(current_row, col, '', cell_format)
                    else:
                        worksheet.write(current_row, col, cell_value, cell_format)


                col = len(fields_to_export)  # Bắt đầu từ cột Kỹ năng
                # Ghi cột Nhóm kỹ năng, Thẻ, Kỹ năng, Mức độ hiện tại, Số điểm
                if skill:
                    skill_group = skill.emp_skill_id.tag_id.skill_group_id.name if skill.emp_skill_id and skill.emp_skill_id.tag_id and skill.emp_skill_id.tag_id.skill_group_id else ''
                    skill_tag = skill.emp_skill_id.tag_id.name if skill.emp_skill_id and skill.emp_skill_id.tag_id else ''
                    skill_name = skill.emp_skill_id.skill_id.name if skill.emp_skill_id and skill.emp_skill_id.skill_id else ''
                    level_name = skill.emp_skill_id.current_level_id.name if skill.emp_skill_id and skill.emp_skill_id.current_level_id else ''
                    score = ''
                    if skill.score:
                        score = str(skill.score) + '%' if skill.score > 0 else ''
                else:
                    skill_group = ''
                    skill_tag = ''
                    skill_name = ''
                    level_name = ''
                    score = ''

                # Cập nhật độ rộng cột
                for value, idx in [(skill_group, col), (skill_tag, col + 1), (skill_name, col + 2), (level_name, col + 3), (str(score), col + 4)]:
                    if len(str(value)) > max_col_widths[idx]:
                        max_col_widths[idx] = len(str(value))

                # Ghi giá trị
                worksheet.write(current_row, col, skill_group, cell_format)
                worksheet.write(current_row, col + 1, skill_tag, cell_format)
                worksheet.write(current_row, col  + 2, skill_name, cell_format)
                worksheet.write(current_row, col + 3, level_name, cell_format)
                worksheet.write(current_row, col + 4, score, cell_format)

                current_row += 1

            # # Merge các cột nhân viên nếu có nhiều hơn 1 kỹ năng
            # if skill_count > 1:
            #     for col, field_name in enumerate(fields_to_export):
            #         # Sử dụng giá trị đã ghi ở dòng đầu
            #         cell_value = cell_values[field_name]
            #         if field_name == 'weight':
            #             value = getattr(record, field_name)
            #             if value is not None:
            #                 if value < 50:
            #                     merge_format = red_format
            #                 elif value < 70:
            #                     merge_format = yellow_format
            #                 else:
            #                     merge_format = green_format
            #             else:
            #                 merge_format = cell_format
            #         else:
            #             merge_format = cell_format
            #         worksheet.merge_range(start_row, col, start_row + skill_count - 1, col, cell_value, merge_format)

        # Set độ rộng cột
        for i, width in enumerate(max_col_widths):
            worksheet.set_column(i, i, width + 2)

        workbook.close()
        output.seek(0)
        excel_file = base64.b64encode(output.read())

        # Tạo attachment
        attachment = self.env['ir.attachment'].create({
            'name': 'Danh_sach_nhan_vien.xlsx',
            'type': 'binary',
            'datas': excel_file,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    # ---- Longkc -----
    def action_compair(self):
        active_ids = self.env.context.get('active_ids', [])

        candidate_search_id = self.env.context.get('candidate_search_id', False)
        # Xây dựng URL với query parameters
        params = {
            'active_ids': ','.join(map(str, active_ids)),  # Chuyển list active_ids thành chuỗi
            'candidate_search_id': candidate_search_id,
        }

        redirect_url = '/candidate/compare?' + urllib.parse.urlencode(params)
        return {
            'type': 'ir.actions.act_url',
            'url': redirect_url,
        }
    # ---- END longkc -----