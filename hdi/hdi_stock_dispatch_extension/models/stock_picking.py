from odoo import models, fields


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    picklist_ids = fields.One2many(
        'picking.picklist',
        'picking_id',
        string='Picklists'
    )
    picklist_count = fields.Integer(
        compute='_compute_picklist_count',
        string='Picklist Count'
    )

    def _compute_picklist_count(self):
        for picking in self:
            picking.picklist_count = len(picking.picklist_ids)

    def action_view_picklists(self):
        self.ensure_one()
        return {
            'name': _('Picklists'),
            'type': 'ir.actions.act_window',
            'res_model': 'picking.picklist',
            'view_mode': 'tree,form',
            'domain': [('picking_id', '=', self.id)],
            'context': {'default_picking_id': self.id},
        }
