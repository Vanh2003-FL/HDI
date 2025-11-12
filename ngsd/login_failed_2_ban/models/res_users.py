import logging

from odoo import api, http, models, fields
from odoo.exceptions import AccessDenied
_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = "res.users"

    def _check_credentials(self, password, user_agent_env=None):
        login_attempt = self.env['login.failed.attempts'].search([('failed_user_id', '=', self.id)], limit=1)
        logged_in = self.env.user.id

        login_failed_attempts = int(self.env["ir.config_parameter"].sudo().get_param("login_failed_2_ban.login_failed_attempts"))
        if login_failed_attempts <= 0:
            return super(ResUsers, self)._check_credentials(password, user_agent_env)
        
        # Kiểm tra nếu tài khoản đã bị khóa do quá nhiều lần đăng nhập thất bại
        if login_attempt and login_attempt.login_failed_number >= login_failed_attempts:
            raise AccessDenied('Tài khoản của bạn bị khóa do đăng nhập thất bại quá nhiều lần. Vui lòng liên hệ Admin để được hỗ trợ')

        try:
            # Kiểm tra kiểu dữ liệu của password
            if str(type(password)) != str("<class 'odoo.api.res.users'>"):
                super(ResUsers, self)._check_credentials(password, user_agent_env)

            # Đặt lại số lần đăng nhập thất bại sau khi đăng nhập thành công
            if logged_in:
                failed_user_id = logged_in
            else:
                failed_user_id = self.id

            if login_attempt:
                login_attempt.sudo().write({'login_failed_number': 0})
            else:
                self.env['login.failed.attempts'].create({
                    'failed_user_id': failed_user_id,
                    'login_failed_number': 0,
                })
        except AccessDenied:
            # Tăng số lần đăng nhập thất bại nếu đăng nhập thất bại
            if login_attempt:
                login_attempt.sudo().write({'login_failed_number': login_attempt.login_failed_number + 1})
            else:
                self.env['login.failed.attempts'].create({
                    'failed_user_id': self.id,
                    'login_failed_number': 1,
                })
            self.env.cr.commit()  # Commit ngay lập tức sau khi cập nhật số lần đăng nhập thất bại
            raise

    def reset_login_failed_number(self):
        login_attempt = self.env['login.failed.attempts'].search([('failed_user_id', '=', self.id)], limit=1)
        login_attempt.sudo().write({'login_failed_number': 0})
