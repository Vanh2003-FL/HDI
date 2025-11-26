from odoo import models, fields, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    receipt_id = fields.Many2one(
        'stock.receipt',
        string='Receipt Extension',
        help='Extended receipt information'
    )
    has_receipt_extension = fields.Boolean(
        compute='_compute_has_receipt_extension',
        string='Has Receipt Extension'
    )

    @api.depends('receipt_id')
    def _compute_has_receipt_extension(self):
        for picking in self:
            picking.has_receipt_extension = bool(picking.receipt_id)

    def action_create_receipt_extension(self):
        self.ensure_one()
        if self.picking_type_code != 'incoming':
            return
        
        if not self.receipt_id:
            receipt = self.env['stock.receipt'].create({
                'picking_id': self.id,
                'receipt_date': fields.Datetime.now(),
            })
            self.receipt_id = receipt.id
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.receipt',
            'res_id': self.receipt_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
