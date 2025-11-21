from odoo import models, fields, api, _, exceptions
from odoo.exceptions import ValidationError
import re

class NGSCScoringCriteria(models.Model):
    _name = 'ngsc.scoring.criteria'
    _description = 'NGSC - Tiêu chí chấm điểm'

    name = fields.Char(string='Tên tiêu chí', required=True)
    type = fields.Selection([
        ('percent', 'Phần trăm (%)'),
        ('point', 'Điểm'),
        ('grade', 'Xếp hạng (A, B, C, D, F)'),
        ('boolean', 'Pass / Fail (T/F)'),
    ], string='Kiểu chấm điểm', required=True)

    version_id = fields.Many2one(
        'ngsc.innovation.version',
        string='Phiên bản',
        ondelete='cascade'
    )

    # Các field lưu thực tế
    max_point_percent = fields.Float(string='Điểm tối đa (%)')
    max_point_point = fields.Float(string='Điểm tối đa (Điểm)')
    max_point_grade = fields.Char(string='Các mức xếp hạng')
    max_point_boolean = fields.Selection([
        ('true', 'Pass'),
        ('false', 'Fail')
    ], string='Giá trị mặc định')

    # Field nhập chung (dùng trong view tree)
    max_point_input = fields.Char(string="Điểm tối đa")

    @api.onchange('type')
    def _onchange_type(self):
        """Khi đổi type, hiển thị giá trị từ field tương ứng vào ô nhập chung"""
        for rec in self:
            if rec.type == 'percent':
                # Hiển thị giá trị kèm ký tự % nếu có giá trị
                rec.max_point_input = f"{rec.max_point_percent}%" if rec.max_point_percent else ''
            elif rec.type == 'point':
                rec.max_point_input = str(rec.max_point_point or '')
            elif rec.type == 'grade':
                rec.max_point_input = rec.max_point_grade or ''
            elif rec.type == 'boolean':
                rec.max_point_input = rec.max_point_boolean or ''

    @api.onchange('max_point_input')
    def _onchange_max_point_input(self):
        """Khi nhập giá trị, kiểm tra và cập nhật vào field thực tế"""
        for rec in self:
            if not rec.max_point_input:
                continue

            try:
                if rec.type == 'percent':
                    # Loại bỏ ký tự % và khoảng trắng, nếu có
                    input_value = rec.max_point_input.strip().rstrip('%')
                    # Kiểm tra giá trị là số thực
                    value = float(input_value)
                    # Kiểm tra số âm
                    if value < 0:
                        raise ValidationError("Điểm tối đa cho kiểu 'Phần trăm (%)' không được là số âm.")
                    rec.max_point_percent = value
                    # Cập nhật lại max_point_input để hiển thị kèm %
                    rec.max_point_input = f"{rec.max_point_percent}%"
                elif rec.type == 'point':
                    # Kiểm tra giá trị là số thực
                    value = float(rec.max_point_input)
                    # Kiểm tra số âm
                    if value < 0:
                        raise ValidationError("Điểm tối đa cho kiểu 'Điểm' không được là số âm.")
                    rec.max_point_point = value
                elif rec.type == 'grade':
                    # Kiểm tra giá trị chỉ chứa A, B, C, D, F (cách nhau bằng dấu phẩy)
                    grades = rec.max_point_input.replace(' ', '').split(',')
                    valid_grades = {'A', 'B', 'C', 'D', 'F'}
                    if not all(grade in valid_grades for grade in grades):
                        raise ValidationError("Điểm tối đa cho kiểu 'Xếp hạng' chỉ được chứa A, B, C, D, F (cách nhau bằng dấu phẩy).")
                    rec.max_point_grade = rec.max_point_input
                elif rec.type == 'boolean':
                    # Chuẩn hóa giá trị nhập vào
                    input_value = rec.max_point_input.strip().lower()
                    if input_value in ['pass', 't', 'true']:
                        rec.max_point_boolean = 'true'
                    elif input_value in ['fail', 'f', 'false']:
                        rec.max_point_boolean = 'false'
                    else:
                        raise ValidationError("Điểm tối đa cho kiểu 'Pass / Fail' chỉ được là 'Pass', 'T', 'True' hoặc 'Fail', 'F', 'False'.")
            except ValueError:
                if rec.type in ['percent', 'point']:
                    raise ValidationError("Điểm tối đa cho kiểu '{}' phải là một số.".format(rec.type == 'percent' and 'Phần trăm (%)' or 'Điểm'))