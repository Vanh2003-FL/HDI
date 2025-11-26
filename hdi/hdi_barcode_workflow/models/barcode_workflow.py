from odoo import models, fields, api, _

class BarcodeWorkflow(models.Model):
    _name = 'barcode.workflow'
    _description = 'Barcode Workflow'
    _order = 'create_date desc'
    
    name = fields.Char(required=True, default=lambda self: _('New'))
    picking_id = fields.Many2one('stock.picking')
    step_ids = fields.One2many('barcode.workflow.step', 'workflow_id')
    current_step = fields.Integer(default=1)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
    ], default='draft')
    
