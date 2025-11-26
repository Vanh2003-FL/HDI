from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ReceiptBatchLine(models.Model):
    _name = 'receipt.batch.line'
    _description = 'Receipt Batch Line'
    _order = 'sequence, id'

    sequence = fields.Integer(string='Sequence', default=10)
    receipt_id = fields.Many2one(
        'stock.receipt',
        string='Receipt',
        required=True,
        ondelete='cascade'
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True
    )
    lot_id = fields.Many2one(
        'stock.lot',
        string='Lot/Serial Number',
        domain="[('product_id', '=', product_id)]"
    )
    lot_name = fields.Char(
        string='Lot/Serial Number',
        help='Enter lot name if not exists'
    )
    quantity = fields.Float(
        string='Quantity',
        required=True,
        digits='Product Unit of Measure'
    )
    uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        related='product_id.uom_id',
        readonly=True
    )
    
    # Package Information
    package_no = fields.Char(
        string='Package Number'
    )
    pallet_no = fields.Char(
        string='Pallet Number'
    )
    
    # Quality Check
    qc_result = fields.Selection([
        ('pass', 'Pass'),
        ('fail', 'Fail'),
        ('pending', 'Pending'),
    ], string='QC Result', default='pending')
    qc_remarks = fields.Text(
        string='QC Remarks'
    )
    
    # Expiry
    expiry_date = fields.Date(
        string='Expiry Date'
    )
    manufacturing_date = fields.Date(
        string='Manufacturing Date'
    )
    
    notes = fields.Char(string='Notes')

    @api.constrains('quantity')
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(_('Quantity must be greater than zero.'))

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id
