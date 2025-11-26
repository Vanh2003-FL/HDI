from odoo import models, fields

class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    vehicle_assign_id = fields.Many2one('picking.vehicle.assign')
    vehicle_id = fields.Many2one('fleet.vehicle', related='vehicle_assign_id.vehicle_id', store=True)
    driver_id = fields.Many2one('res.partner', related='vehicle_assign_id.driver_id', store=True)
