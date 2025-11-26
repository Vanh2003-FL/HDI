from odoo import models, fields, api

class StockReportEntry(models.Model):
    _name = 'stock.report.entry'
    _description = 'Stock Report Entry'
    _order = 'report_date desc'
    
    name = fields.Char(required=True)
    report_type = fields.Selection([
        ('receipt', 'Receipt Report'),
        ('dispatch', 'Dispatch Report'),
        ('inventory', 'Inventory Report'),
        ('movement', 'Movement Report'),
    ], required=True)
    report_date = fields.Date(required=True)
    warehouse_id = fields.Many2one('stock.warehouse')
    
    # Metrics
    total_receipts = fields.Integer()
    total_dispatches = fields.Integer()
    total_inventory_value = fields.Float()
    movements_count = fields.Integer()
    
    # JSON data for detailed reports
    report_data = fields.Text()
