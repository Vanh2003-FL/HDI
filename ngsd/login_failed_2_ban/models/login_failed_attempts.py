from odoo import models, fields, api


class LoginFailedAttempts(models.Model):
    _name = 'login.failed.attempts'
    _description = 'Login Failed Attempts'

    failed_user_id = fields.Many2one('res.users', string='User', required=True, ondelete='cascade')
    login_failed_number = fields.Integer(string='Failed Login Attempts', default=0)

