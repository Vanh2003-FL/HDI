# -*- coding: utf-8 -*-
from odoo import models, fields, api, _, exceptions
from lxml import etree
from odoo.exceptions import UserError


class DashboardPowerbi(models.Model):
    _description = 'Dashboard PowerBI'
    _name = "dashboard.powerbi"
    _order="sequence"

    sequence = fields.Integer('Thứ tự',default='1')
    ref = fields.Char('Mã báo cáo')
    name = fields.Char('Tên báo cáo', required=1)
    iframe = fields.Html('Mã nhúng', required=1, sanitize=False)
    groups_id = fields.Many2many('res.groups',string='Nhóm quyền được xem báo cáo')
    company_id = fields.Many2one('res.company', string='Công ty')

    menu_id = fields.Many2one('ir.ui.menu', string="Menu", readonly=True)
    action_id = fields.Many2one('ir.actions.client', string="Hành động", readonly=True)
    thumbnail = fields.Image('Thumbnail')

    def _prepare_menu(self):
        return {
            "name": self.name,
            "groups_id": self.groups_id.ids,
            "parent_id": self.env.ref("ngs_powerbi.powerbi_dashboard_line_menu").id,
            "action": "ir.actions.client,%s" % self.action_id.id,
        }

    def _prepare_action(self):
        return {
            "name": self.name,
            "type": "ir.actions.client",
            "tag": 'powerbi_dashboard',
            "context": "{'id': %s }"%self.id
        }

    @api.model
    def create(self, vals_list):
        rec = super(DashboardPowerbi, self).create(vals_list)
        # if not rec.action_id:
        #     action_id = self.env['ir.actions.client'].sudo().create(rec._prepare_action())
        #     rec.action_id = action_id.id
        # if not rec.menu_id:
            # menu_id = self.env['ir.ui.menu'].sudo().create(rec._prepare_menu())
            # rec.menu_id = menu_id.id
        return rec

    def write(self, values):
        res = super(DashboardPowerbi, self).write(values)
        # for rec in self:
        #     rec.menu_id.sudo().write({'name': rec.name, 'groups_id': rec.groups_id.ids})
        return res

    def unlink(self):
        for rec in self:
            if rec.action_id:
                rec.action_id.sudo().unlink()
            if rec.menu_id:
                rec.menu_id.sudo().unlink()
        return super(DashboardPowerbi, self).unlink()

    @api.model
    def get_iframe(self, id):
        rec = self.browse(id)
        style = ' style="position:fixed; top:100px; height:85%; left:0; bottom:0; right:0; width:100%; border:none; margin:0; padding:0; overflow:hidden;"'
        rec_iframe = rec.iframe
        index = rec_iframe.find('<iframe')
        iframe = rec_iframe[:index+7] + style + rec_iframe[index+7:]
        return iframe

