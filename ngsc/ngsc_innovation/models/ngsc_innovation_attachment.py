from odoo import models, fields


class NgscInnovationAttachment(models.Model):
    _name = 'ngsc.innovation.attachment'
    _description = 'Innovation Attachment'

    name = fields.Char(string='Tên tệp đính kèm', required=True)
    datas_fname = fields.Char(string="Tên tập tin")
    datas = fields.Binary(string='Tệp tải lên', required=True)
    idea_id = fields.Many2one('ngsc.innovation.idea', string='Innovation Idea', ondelete='cascade', required=True)
