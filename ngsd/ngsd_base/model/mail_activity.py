# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError
from datetime import datetime, date


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    @api.model_create_multi
    def create(self, vals_list):
        activities = super(MailActivity, self).create(vals_list)
        for activity in activities:
            if activity.res_model == 'crm.lead':
                mes = f"""Bạn đã được phân công một hoạt động"""
                self.env[activity.res_model].browse(activity.res_id).res.send_notify(mes, activity.user_id)
        return activities
