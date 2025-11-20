from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_en_use_quote = fields.Boolean(string="Không sử dụng báo giá", implied_group='ngsd_base.group_en_use_quote')

    en_ot_day_limit = fields.Float(string="Theo ngày", config_parameter="ngsd_base.en_ot_day_limit", default=0, help="Giờ làm thêm tối đa của một nhân viên trong ngày, giá trị 0 nghĩa là không giới hạn thời gian.")
    en_ot_month_limit = fields.Float(string="Theo tháng", config_parameter="ngsd_base.en_ot_month_limit", default=0, help="Giờ làm thêm tối đa của một nhân viên trong tháng, giá trị 0 nghĩa là không giới hạn thời gian.")
    en_ot_year_limit = fields.Float(string="Theo năm", config_parameter="ngsd_base.en_ot_year_limit", default=0, help="Giờ làm thêm tối đa của một nhân viên trong năm, giá trị 0 nghĩa là không giới hạn thời gian.")
    en_ot_warning = fields.Selection(string="Cảnh báo khi đạt giới hạn", selection=[('ban', 'Không được tạo'), ('warning', 'Cảnh báo')], config_parameter="ngsd_base.en_ot_warning", default='ban', help='''Lựa chọn cách hệ thống cảnh báo khi nhân viên đạt đến giới hạn tăng ca được cài đặt\n
                                                                                                                                                                                                                    Không được tạo: Không có phép nhân viên tạo yêu cầu tăng ca khi đã vượt quá số giờ giới hạn\n
                                                                                                                                                                                    Cảnh báo: Cho phép yêu cầu tăng ca, nhưng hiển thị cảnh báo khi số giờ tăng ca của nhân viên vượt quá giới hạn''')

    en_fiscal_year_id = fields.Many2one('en.fiscal.year', string="Năm tài chính", config_parameter="en_fiscal_year_id")
