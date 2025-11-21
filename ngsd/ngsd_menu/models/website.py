from werkzeug.useragents import UserAgent
from odoo import models, fields, api
from datetime import datetime, date, time, timedelta

from odoo.http import request


class Website(models.Model):
    _inherit = 'website'

    def get_happy_birthday(self):
        self = self.sudo()
        employee = self.env['hr.employee'].search([('birthday', '!=', False)], order='birthday asc')
        hpbd = []
        hpbd_upcomming = []
        for rec in employee:
            if datetime.now().day <= rec.birthday.day and datetime.now().month == rec.birthday.month:
                hpbd.append({"name": rec.display_name, 'birthday': rec.birthday, 'image': rec.image_1920, 'department': rec.department_id.name})
        if hpbd:
            hpbd = sorted(hpbd, key=lambda x: x.get('birthday').day)
        return hpbd, hpbd_upcomming

    def get_image_and_url(self):
        attribute = []
        images = self.env['website.page'].search([('name', '=', 'Home')])[0].image_ids
        for rec in images:
            attribute.append({'image': rec.image_event, 'url': rec.url_event, 'name': rec.name_event, 'date': rec.date_event})
        return attribute
    def is_mobile_home_page(self):
        user_agent = UserAgent(request.httprequest.user_agent.string)
        #user_agent = request.httprequest.user_agent_class(request.httprequest.user_agent.string)
        if user_agent.platform in ['android', 'iphone', 'ipad']:
            return True
        else:
            return False


class WebsiteImage(models.Model):
    _inherit = 'website.page'

    image_ids = fields.One2many(comodel_name='website.image', inverse_name='page_id', string='Ảnh sự kiện')

class WebsiteImage(models.Model):
    _name = 'website.image'
    _description = 'Website Image'

    image_event = fields.Image(string='Ảnh sự kiện')
    url_event = fields.Char(string='Link')
    page_id = fields.Many2one(comodel_name='website.page', string='Page', ondelete='cascade')
    name_event = fields.Char(string='Tên sự kiện', required=True)
    date_event = fields.Datetime(string='Thời gian sự kiện')

class BlogPost(models.Model):
    _inherit = "blog.post"

    pdf_attachment = fields.Binary(string="Đính kèm")
    pdf_attachment_name = fields.Char(string='Tên tập đính kèm')
    pdf_attachment_id = fields.Char(string='id_pdf_attachment', compute='compute_pdf_integer')

    @api.depends('pdf_attachment')
    def compute_pdf_integer(self):
        self = self.sudo()
        for rec in self:
            ir_attachment = self.env['ir.attachment'].search([('res_model', '=', rec._name), ('res_id', '=', rec.id), ('res_field', '=', 'pdf_attachment')], limit=1)
            rec.pdf_attachment_id = ir_attachment.id
            ir_attachment.write({
                'name': rec.pdf_attachment_name
            })


