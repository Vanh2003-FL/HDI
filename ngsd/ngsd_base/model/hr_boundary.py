import datetime

from odoo import models, fields, api


class HrBoundary(models.Model):
    _name = "hr.boundary"
    _description = "Định biên"

    block_id = fields.Many2one(comodel_name='en.name.block', string='Khối')
    department_id = fields.Many2one(comodel_name='hr.department', string='Trung tâm/Ban', required=True)
    en_department_id = fields.Many2one(comodel_name='en.department', string='Phòng')
    hr_job_id = fields.Many2one(comodel_name='hr.job', string='Vị trí công việc')
    en_name_level_id = fields.Many2one(comodel_name='en.name.level', string='Cấp bậc', required=True)
    month = fields.Selection([('1', '1'),
        ('2', '2'),
        ('3', '3'),
        ('4', '4'),
        ('5', '5'),
        ('6', '6'),
        ('7', '7'),
        ('8', '8'),
        ('9', '9'),
        ('10', '10'),
        ('11', '11'),
        ('12', '12')], string='Tháng', required=True)
    year = fields.Selection(string="Năm", selection=lambda self: self._calculator_year_selection(),default=False, required=True)
    hr_boundary = fields.Integer(string='Định biên')
    version = fields.Char(string='Phiên bản', compute='compute_version')
    active = fields.Boolean(string='Hoạt động', default=True)
    number_version = fields.Integer(string='Số phiên bản', readonly=True)

    @api.depends('number_version')
    def compute_version(self):
        for rec in self:
            rec.version = 'V%s' % str(rec.number_version or 1).zfill(5)

    def _calculator_year_selection(self):
        return [(str(i),str(i)) for i in range(2019, 2031)]


    @api.model
    def create(self, val):
        old_version = self.sudo().search([('department_id', '=', val.get('department_id')), ('en_name_level_id', '=', val.get('en_name_level_id')), ('year', '=', val.get('year')), ('month', '=', val.get('month'))], order='number_version desc', limit=1)
        if old_version:
            val['number_version'] = old_version.number_version + 1
        else:
            val['number_version'] = 1
        val.update({
            'block_id': self.env['hr.department'].browse(val.get('department_id')).block_id.id,
        })
        res = super().create(val)
        list_fields = ['department_id', 'en_department_id', 'hr_job_id', 'hr_boundary', 'version', 'active']
        old_version_master = self.env['hr.boundary.master'].sudo().search([('department_id', '=', res.department_id.id), ('en_name_level_id', '=', res.en_name_level_id.id), ('year', '=',res.year), ('month', '=', res.month)], order='number_version desc', limit=1)
        val_update = {
            'block_id': res.block_id.id,
            'en_department_id': res.en_department_id.id,
            'hr_job_id': res.hr_job_id.id,
            'hr_boundary': res.hr_boundary,
            'version': res.version,
            'active': res.active,
        }
        if old_version_master:
            old_version_master.write(val_update)
        else:
            val_update.update({
                'department_id': res.department_id.id,
                'en_name_level_id': res.en_name_level_id.id,
                'year': res.year,
                'month': res.month,
            })
            self.env['hr.boundary.master'].create(val_update)
        return res


class HrBoundaryMaster(models.Model):
    _name = "hr.boundary.master"
    _description = "Định biên"

    block_id = fields.Many2one(comodel_name='en.name.block', string='Khối')
    department_id = fields.Many2one(comodel_name='hr.department', string='Trung tâm/Ban', required=True)
    en_department_id = fields.Many2one(comodel_name='en.department', string='Phòng')
    hr_job_id = fields.Many2one(comodel_name='hr.job', string='Vị trí công việc')
    en_name_level_id = fields.Many2one(comodel_name='en.name.level', string='Cấp bậc', required=True)
    month = fields.Selection([('1', '1'),
                              ('2', '2'),
                              ('3', '3'),
                              ('4', '4'),
                              ('5', '5'),
                              ('6', '6'),
                              ('7', '7'),
                              ('8', '8'),
                              ('9', '9'),
                              ('10', '10'),
                              ('11', '11'),
                              ('12', '12')], string='Tháng', required=True)
    year = fields.Selection(string="Năm", selection=lambda self: self._calculator_year_selection(), required=True)
    hr_boundary = fields.Integer(string='Định biên')
    version = fields.Char(string='Phiên bản', compute='compute_version')
    active = fields.Boolean(string='Hoạt động', default=True)
    number_version = fields.Integer(string='Số phiên bản', readonly=True)
    date = fields.Date(string='Ngày', compute='_get_date', store=True)

    def _calculator_year_selection(self):
        return [(str(i), str(i)) for i in range(2019, 2031)]

    @api.depends('month', 'year')
    def _get_date(self):
        for rec in self:
            if rec.month and rec.year:
                rec.date = datetime.date(int(rec.year), int(rec.month), 1)
            else:
                rec.date = False
