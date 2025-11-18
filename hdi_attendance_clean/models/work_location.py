# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class HdiWorkLocation(models.Model):
    _name = 'hdi.work.location'
    _description = 'HDI Work Location'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Location Name', required=True, tracking=True)
    address = fields.Text(string='Address')
    
    latitude = fields.Float(string='Latitude', digits=(10, 7), required=True)
    longitude = fields.Float(string='Longitude', digits=(10, 7), required=True)
    radius = fields.Float(string='Allowed Radius (meters)', default=100.0, help='Maximum distance from location center')
    
    active = fields.Boolean(string='Active', default=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    
    attendance_count = fields.Integer(string='Attendance Count', compute='_compute_attendance_count')
    
    def _compute_attendance_count(self):
        for record in self:
            record.attendance_count = self.env['hdi.attendance'].search_count([
                ('work_location_id', '=', record.id)
            ])
    
    def action_view_attendances(self):
        self.ensure_one()
        return {
            'name': _('Attendances'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.attendance',
            'view_mode': 'list,form',
            'domain': [('work_location_id', '=', self.id)],
            'context': {'default_work_location_id': self.id}
        }
