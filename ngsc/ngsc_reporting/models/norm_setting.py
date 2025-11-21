import re

from odoo import models, fields, api, _, exceptions
from odoo.exceptions import ValidationError


class NormSetting(models.Model):
    _name = 'reporting.norm.setting'
    _description = "Cấu hình Norm"

    name = fields.Char(string='Tên cấu hình', required=True)
    short_name = fields.Char(string='Tên viết tắt', required=True)
    norm_value = fields.Integer(string='Giá trị NORM (%)', required=True, default=100)
    standard_deviation = fields.Integer(string='Độ lệch chuẩn (%)', required=True, default=10)
    satisfactory_direction = fields.Selection([
        ('ge', 'Lớn hơn hoặc bằng'),
        ('le', 'Nhỏ hơn hoặc bằng')],
        required=True, default='le', string='Chiều đánh giá')

    color_good = fields.Char(string='Màu đánh giá tốt', default='#ff00ff')
    color_pass = fields.Char(string='Màu đánh giá đạt', default='#6aa84e')
    color_fail = fields.Char(string='Màu đánh giá chưa đạt', default='#ff0000')
    color_bad = fields.Char(string='Màu đánh giá kém', default='#00ffff')

    _sql_constraints = [
        ('short_name_uniq', 'unique (short_name)',
         'Tên viết tắt phải là duy nhất'),
    ]

    @api.constrains('color_good', 'color_pass', 'color_fail', 'color_bad')
    def _check_color_format(self):
        for record in self:
            for field in ['color_good', 'color_pass', 'color_fail', 'color_bad']:
                color = getattr(record, field)
                if color and not re.match(r'^#[0-9A-Fa-f]{6}$', color):
                    raise ValidationError(f"{field} must be a valid hex code (e.g., #FF0000)")

    def write(self, vals):
        return super().write(vals)

    def get_color_for_index(self, value):
        norm = self.norm_value/100
        standard = self.standard_deviation/100

        if self.standard_deviation == 'le':
            if value <= (norm - standard):
                return self.color_good
            elif norm >= value > (norm - standard):
                return self.color_pass
            elif norm < value <= (norm + standard):
                return self.color_fail
            else:
                return self.color_bad
        else:
            if value >= (norm + standard):
                return self.color_good
            elif norm >= value > (norm + standard):
                return self.color_pass
            elif norm > value >= (norm - standard):
                return self.color_fail
            else:
                return self.color_bad

    @api.model
    def get_norm_popup_data(self):
        norms = self.search([])
        result = []
        name = {
            '%SA1':'% Schedule Achievement v1.0',
            '%SA2': '% Schedule Achievement v2.0',
            '%SAL': '% Schedule Achievement v lastupdate',
            '%EEB1': '% Effort Efficiency BMM đầu tiên',
            '%EEBL': '% Effort Efficiency BMM cuối cùng',
            '%EEP1': '% Effort Efficiency Plan v1.0',
            '%EEP2': '% Effort Efficiency Plan v2.0',
            '%EEPL': '% Effort Efficiency Plan v lastupdate',
            '%EEM': '% Effort Efficiency Monthly',
        }
        for idx, n in enumerate(norms, start=1):
            norm = n.norm_value / 100
            std = n.standard_deviation / 100
            if n.satisfactory_direction == 'le':
                thresholds = {
                    'good': f"<= {norm - std:.2f}",
                    'pass': f"<= {norm:.2f}",
                    'norm': f"{norm:.2f}",
                    'fail': f"<= {norm + std:.2f}",
                    'bad': f"> {norm + std:.2f}"
                }
            else:  # ge
                thresholds = {
                    'good': f">= {norm + std:.2f}",
                    'pass': f">= {norm:.2f}",
                    'norm': f"{norm:.2f}",
                    'fail': f">= {norm - std:.2f}",
                    'bad': f"< {norm - std:.2f}"
                }
            result.append({
                'stt': idx,
                'short_name': name.get(n.short_name),
                'norm': n.norm_value,
                'std': n.standard_deviation,
                'direction': n.satisfactory_direction,
                'thresholds': thresholds,
                'colors': {
                    'good': n.color_good,
                    'pass': n.color_pass,
                    'fail': n.color_fail,
                    'bad': n.color_bad,
                }
            })
        return result


