from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class BarcodeItem(models.Model):
    """Hàng lẻ không có Batch - quản lý từng barcode riêng lẻ"""
    _name = 'barcode.item'
    _description = 'Barcode Item (Loose Items without Batch)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Barcode',
        required=True,
        index=True,
        help='Individual product barcode'
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        index=True
    )
    location_id = fields.Many2one(
        'stock.location',
        string='Current Location',
        required=True,
        domain=[('usage', '=', 'internal')]
    )
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('scanned', 'Scanned'),
        ('placed', 'Placed in Location'),
        ('confirmed', 'Confirmed'),
        ('out', 'Out of Stock'),
    ], string='Status', default='draft', tracking=True)
    
    # Receipt information
    receipt_id = fields.Many2one(
        'stock.receipt',
        string='Receipt Reference'
    )
    receipt_date = fields.Datetime(
        string='Receipt Date',
        default=fields.Datetime.now
    )
    
    # Picking information (for outbound)
    picking_id = fields.Many2one(
        'stock.picking',
        string='Picking Reference'
    )
    picked_date = fields.Datetime(
        string='Picked Date'
    )
    
    # Additional info
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company
    )

    _sql_constraints = [
        ('barcode_unique', 'unique(name, company_id)', 
         'Barcode must be unique per company!')
    ]

    @api.constrains('name')
    def _check_barcode(self):
        for item in self:
            if not item.name:
                raise ValidationError(_('Barcode cannot be empty.'))

    def action_scan(self):
        """Action when barcode is scanned"""
        self.ensure_one()
        self.state = 'scanned'

    def action_place(self, location_id):
        """Action to place item in a location"""
        self.ensure_one()
        self.write({
            'location_id': location_id,
            'state': 'placed',
        })

    def action_confirm(self):
        """Confirm item placement"""
        self.ensure_one()
        self.state = 'confirmed'

    def action_pick(self, picking_id):
        """Action when item is picked for outbound"""
        self.ensure_one()
        self.write({
            'picking_id': picking_id,
            'picked_date': fields.Datetime.now(),
            'state': 'out',
        })
