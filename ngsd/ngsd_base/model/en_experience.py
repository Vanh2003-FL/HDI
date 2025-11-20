from odoo import models, fields


class ENExperience(models.Model):
    _name = 'en.experience'
    _description = 'Bài học kinh nghiệm'

    name = fields.Char('Bài học kinh nghiệm')
    type = fields.Selection(selection=[('lesson', 'Bài học thương đau'), ('experience', 'Chia sẻ kinh nghiệm')], string='Loại bài học')
    project_id = fields.Many2one('project.project', 'Dự án')
    description = fields.Text(string='Nội dung')
