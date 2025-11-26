from odoo import models, fields, api, _

class OddItem(models.Model):
    _name = 'odd.item'
    _description = 'Odd Item Management'
    
    name = fields.Char(required=True, default=lambda self: _('New'))
    product_id = fields.Many2one('product.product', required=True)
    location_id = fields.Many2one('stock.location', required=True)
    lot_id = fields.Many2one('stock.lot')
    quantity = fields.Float(required=True)
    reason = fields.Selection([
        ('damaged', 'Damaged'),
        ('incomplete', 'Incomplete Lot'),
        ('sample', 'Sample'),
        ('return', 'Customer Return'),
    ], string='Reason')
    state = fields.Selection([
        ('pending', 'Pending'),
        ('resolved', 'Resolved'),
    ], default='pending')
    notes = fields.Text()

class StockQuant(models.Model):
    _inherit = 'stock.quant'
    
    is_odd = fields.Boolean(string='Is Odd Item', default=False)
    odd_reason = fields.Char(string='Odd Reason')
