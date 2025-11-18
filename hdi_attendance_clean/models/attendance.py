# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime


class HdiAttendance(models.Model):
    _name = 'hdi.attendance'
    _description = 'HDI Attendance Record'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'check_in desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default='New')
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, tracking=True)
    
    check_in = fields.Datetime(string='Check In', required=True, default=fields.Datetime.now, tracking=True)
    check_out = fields.Datetime(string='Check Out', tracking=True)
    
    work_location_id = fields.Many2one('hdi.work.location', string='Work Location', tracking=True)
    
    # GPS coordinates
    checkin_latitude = fields.Float(string='Check-in Latitude', digits=(10, 7))
    checkin_longitude = fields.Float(string='Check-in Longitude', digits=(10, 7))
    checkout_latitude = fields.Float(string='Check-out Latitude', digits=(10, 7))
    checkout_longitude = fields.Float(string='Check-out Longitude', digits=(10, 7))
    
    worked_hours = fields.Float(string='Worked Hours', compute='_compute_worked_hours', store=True)
    
    status = fields.Selection([
        ('checkin', 'Checked In'),
        ('checkout', 'Checked Out'),
    ], string='Status', compute='_compute_status', store=True)
    
    note = fields.Text(string='Note')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    
    @api.depends('check_in', 'check_out')
    def _compute_worked_hours(self):
        for record in self:
            if record.check_in and record.check_out:
                delta = record.check_out - record.check_in
                record.worked_hours = delta.total_seconds() / 3600.0
            else:
                record.worked_hours = 0.0
    
    @api.depends('check_in', 'check_out')
    def _compute_status(self):
        for record in self:
            if record.check_out:
                record.status = 'checkout'
            else:
                record.status = 'checkin'
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('hdi.attendance') or 'New'
        return super(HdiAttendance, self).create(vals)
    
    @api.constrains('check_in', 'check_out')
    def _check_validity(self):
        for record in self:
            if record.check_out and record.check_out < record.check_in:
                raise ValidationError(_('Check-out time cannot be earlier than check-in time.'))
    
    def action_checkout(self):
        self.ensure_one()
        if self.check_out:
            raise ValidationError(_('Already checked out.'))
        self.write({
            'check_out': fields.Datetime.now(),
        })
        return True
