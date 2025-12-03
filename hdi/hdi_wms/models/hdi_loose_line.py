# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class HdiLooseLine(models.Model):

    _name = 'hdi.loose.line'
    _description = 'Loose Items Line'
    _order = 'picking_id, sequence, id'
    
    # ===== REFERENCE =====
    sequence = fields.Integer(string='Sequence', default=10)
    
    picking_id = fields.Many2one(
        'stock.picking',
        string='Picking',
        required=True,
        ondelete='cascade',
        index=True,
    )
    
    move_id = fields.Many2one(
        'stock.move',
        string='Stock Move',
        help="Link to core stock.move"
    )
    
    # ===== PRODUCT INFO =====
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
    )
    
    product_uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        required=True,
    )
    
    quantity = fields.Float(
        string='Quantity',
        required=True,
        digits='Product Unit of Measure',
    )
    
    # ===== LOCATION =====
    location_id = fields.Many2one(
        'stock.location',
        string='Source Location',
        required=True,
    )
    
    location_dest_id = fields.Many2one(
        'stock.location',
        string='Destination Location',
        required=True,
    )
    
    # ===== TRACKING =====
    lot_id = fields.Many2one(
        'stock.lot',
        string='Lot/Serial Number',
    )
    
    barcode_scanned = fields.Char(
        string='Scanned Barcode',
    )
    
    # ===== STATUS =====
    state = fields.Selection([
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='State', default='pending')
    
    notes = fields.Text(string='Notes')
    
    company_id = fields.Many2one(
        'res.company',
        related='picking_id.company_id',
        store=True,
        readonly=True,
    )
    
    @api.model
    def create(self, vals):
        """
        ✅ Khi tạo loose line, tạo stock.move tương ứng (core)
        Không được tách rời khỏi core inventory flow
        """
        result = super().create(vals)
        
        # Create corresponding stock.move if not exists
        if not result.move_id and result.picking_id:
            move_vals = {
                'name': result.product_id.name,
                'product_id': result.product_id.id,
                'product_uom': result.product_uom_id.id,
                'product_uom_qty': result.quantity,
                'location_id': result.location_id.id,
                'location_dest_id': result.location_dest_id.id,
                'picking_id': result.picking_id.id,
                'loose_line_id': result.id,
                'company_id': result.company_id.id,
            }
            move = self.env['stock.move'].create(move_vals)
            result.move_id = move.id
        
        return result
    
    def write(self, vals):
        """
        ✅ Update stock.move khi loose line thay đổi
        """
        result = super().write(vals)
        
        # Sync changes to stock.move
        move_vals = {}
        if 'quantity' in vals:
            move_vals['product_uom_qty'] = vals['quantity']
        if 'location_id' in vals:
            move_vals['location_id'] = vals['location_id']
        if 'location_dest_id' in vals:
            move_vals['location_dest_id'] = vals['location_dest_id']
        
        if move_vals:
            for line in self:
                if line.move_id:
                    line.move_id.write(move_vals)
        
        return result
    
    def action_process(self):
        """Mark as processing"""
        self.write({'state': 'processing'})
    
    def action_done(self):
        """
        Mark as done
        ✅ Trigger stock.move done (core)
        """
        for line in self:
            if line.move_id and line.move_id.state not in ['done', 'cancel']:
                line.move_id._action_done()
            line.state = 'done'
