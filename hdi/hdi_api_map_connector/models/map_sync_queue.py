from odoo import models, fields, api

class MapSyncQueue(models.Model):
    _name = 'map.sync.queue'
    _description = 'Map Sync Queue'
    _order = 'create_date desc'
    
    name = fields.Char(required=True)
    sync_type = fields.Selection([
        ('location', 'Location Update'),
        ('quant', 'Inventory Update'),
        ('movement', 'Stock Movement'),
    ], required=True)
    location_id = fields.Many2one('stock.location')
    data_json = fields.Text(string='JSON Data')
    state = fields.Selection([
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('done', 'Done'),
        ('error', 'Error'),
    ], default='pending')
    error_msg = fields.Text()
    sync_date = fields.Datetime()
