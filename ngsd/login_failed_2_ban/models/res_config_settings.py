from odoo import api, models, tools, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    login_failed_attempts = fields.Integer(string="Số lần đăng nhập thất bại", config_parameter="login_failed_2_ban.login_failed_attempts", default=10, help="Tài khoản người dùng sẽ bị khóa sau số lần đăng nhập thất bại này")
