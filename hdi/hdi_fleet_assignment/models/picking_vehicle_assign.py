from odoo import models, fields, api

class PickingVehicleAssign(models.Model):
    _name = 'picking.vehicle.assign'
    _description = 'Picking Vehicle Assignment'
    
    name = fields.Char(required=True)
    picking_ids = fields.Many2many('stock.picking', string='Deliveries')
    vehicle_id = fields.Many2one('fleet.vehicle', required=True)
    driver_id = fields.Many2one('res.partner', required=True)
    route = fields.Text()
    assignment_date = fields.Date(default=fields.Date.today)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('assigned', 'Assigned'),
        ('in_transit', 'In Transit'),
        ('done', 'Done'),
    ], default='draft')
    
