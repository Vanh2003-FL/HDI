# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StockPicking(models.Model):

    _inherit = 'stock.picking'

    batch_ids = fields.One2many(
        'hdi.batch',
        'picking_id',
        string='Batches',
        help="All batches created from this picking"
    )

    batch_count = fields.Integer(
        compute='_compute_batch_count',
        string='Batch Count',
    )

    wms_state = fields.Selection([
        ('none', 'No WMS'),
        ('batch_creation', 'Batch Creation'),
        ('putaway_pending', 'Putaway Pending'),
        ('putaway_done', 'Putaway Done'),
        ('picking_ready', 'Ready to Pick'),
        ('picking_progress', 'Picking in Progress'),
        ('wms_done', 'WMS Complete'),
    ], string='WMS State', default='none', tracking=True,
        help="WMS workflow state - parallel to Odoo core picking state")

    use_batch_management = fields.Boolean(
        string='Use Batch Management',
        default=False,
        help="Enable batch/LPN management for this picking"
    )

    require_putaway_suggestion = fields.Boolean(
        string='Require Putaway Suggestion',
        compute='_compute_require_putaway',
        store=True,
        help="Auto-enabled for incoming pickings"
    )

    loose_line_ids = fields.One2many(
        'hdi.loose.line',
        'picking_id',
        string='Loose Items',
        help="Items not in any batch (loose picking)"
    )

    # ===== SCANNER SUPPORT =====
    last_scanned_barcode = fields.Char(
        string='Last Scanned',
        readonly=True,
    )

    scan_mode = fields.Selection([
        ('none', 'No Scanning'),
        ('batch', 'Scan Batch'),
        ('product', 'Scan Product'),
        ('location', 'Scan Location'),
    ], string='Scan Mode', default='none')

    @api.depends('picking_type_id', 'picking_type_id.code')
    def _compute_require_putaway(self):
        """Auto-enable putaway for incoming pickings"""
        for picking in self:
            picking.require_putaway_suggestion = (
                    picking.picking_type_id.code == 'incoming'
            )

    @api.depends('batch_ids')
    def _compute_batch_count(self):
        """Count batches in this picking"""
        for picking in self:
            picking.batch_count = len(picking.batch_ids)

    def action_create_batch(self):
        self.ensure_one()
        return {
            'name': _('Create Batch'),
            'type': 'ir.actions.act_window',
            'res_model': 'hdi.batch.creation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_picking_id': self.id,
                'default_location_id': self.location_dest_id.id,
            }
        }

    def action_suggest_putaway_all(self):
        self.ensure_one()
        if not self.batch_ids:
            raise UserError(_('No batches found in this picking.'))

        return {
            'name': _('Suggest Putaway for All Batches'),
            'type': 'ir.actions.act_window',
            'res_model': 'hdi.putaway.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_picking_id': self.id,
                'default_batch_ids': [(6, 0, self.batch_ids.ids)],
            }
        }

    def action_open_scanner(self):
        self.ensure_one()
        return {
            'name': _('Scanner - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(self.env.ref('hdi_wms.view_picking_form_scanner').id, 'form')],
            'target': 'fullscreen',
        }

    def action_view_batches(self):
        self.ensure_one()
        return {
            'name': _('Batches - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'hdi.batch',
            'view_mode': 'list,form,kanban',
            'domain': [('picking_id', '=', self.id)],
            'context': {
                'default_picking_id': self.id,
                'default_location_id': self.location_dest_id.id,
            }
        }

    def button_validate(self):

        for picking in self:
            if picking.use_batch_management and picking.require_putaway_suggestion:
                pending_batches = picking.batch_ids.filtered(
                    lambda b: b.state not in ['stored', 'shipped', 'cancel']
                )
                if pending_batches:
                    raise UserError(_(
                        'Cannot validate picking: %d batches are not yet stored.\n'
                        'Please complete putaway for all batches first.'
                    ) % len(pending_batches))

        result = super().button_validate()

        # WMS post-validation
        for picking in self:
            if picking.use_batch_management and picking.state == 'done':
                picking.wms_state = 'wms_done'

        return result

    def action_assign(self):
        result = super().action_assign()

        # Update WMS state after assignment
        for picking in self:
            if picking.use_batch_management and picking.state == 'assigned':
                picking.wms_state = 'picking_ready'

        return result

    def on_barcode_scanned(self, barcode):
        self.ensure_one()
        self.last_scanned_barcode = barcode

        if self.scan_mode == 'batch':
            # Find batch by barcode
            batch = self.env['hdi.batch'].search([
                ('barcode', '=', barcode),
                ('picking_id', '=', self.id),
            ], limit=1)
            if batch:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Batch Found'),
                        'message': _('Batch %s scanned') % batch.name,
                        'type': 'success',
                        'sticky': False,
                    }
                }

        elif self.scan_mode == 'product':
            # Find product by barcode
            product = self.env['product.product'].search([
                ('barcode', '=', barcode),
            ], limit=1)
            if product:
                # Check if product is in move lines
                move_line = self.move_line_ids.filtered(
                    lambda ml: ml.product_id == product
                )
                if move_line:
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': _('Product Found'),
                            'message': _('Product %s scanned') % product.name,
                            'type': 'success',
                            'sticky': False,
                        }
                    }

        # Barcode not found
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Not Found'),
                'message': _('Barcode %s not recognized') % barcode,
                'type': 'warning',
                'sticky': False,
            }
        }
