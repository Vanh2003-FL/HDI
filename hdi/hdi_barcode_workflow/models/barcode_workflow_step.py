from odoo import models, fields

class BarcodeWorkflowStep(models.Model):
    _name = 'barcode.workflow.step'
    _description = 'Barcode Workflow Step'
    _order = 'sequence'
    
    sequence = fields.Integer(default=10)
    workflow_id = fields.Many2one('barcode.workflow', required=True, ondelete='cascade')
    step_type = fields.Selection([
        ('scan_location', 'Scan Location'),
        ('scan_product', 'Scan Product'),
        ('scan_lot', 'Scan Lot'),
        ('confirm_qty', 'Confirm Quantity'),
    ], required=True)
    scanned_value = fields.Char()
    is_completed = fields.Boolean(default=False)
