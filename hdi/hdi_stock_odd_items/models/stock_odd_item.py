# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class StockOddItem(models.Model):
    _name = 'stock.odd.item'
    _description = 'Odd Stock Item Management'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(string='Odd Item Reference', required=True, copy=False,
                      default=lambda self: _('New'), readonly=True, tracking=True)
    
    # Product info
    product_id = fields.Many2one('product.product', string='Product', required=True,
                                tracking=True, domain=[('type', '=', 'product')],
                                states={'done': [('readonly', True)]})
    
    # Quantity details
    quantity = fields.Float(string='Odd Quantity', required=True, digits='Product Unit of Measure',
                           tracking=True, states={'done': [('readonly', True)]})
    product_uom_id = fields.Many2one(related='product_id.uom_id', string='UoM')
    
    standard_pack_qty = fields.Float(related='product_id.standard_pack_qty',
                                    string='Standard Pack Qty')
    percentage_of_standard = fields.Float(string='% of Standard Pack',
                                         compute='_compute_percentage', store=True)
    
    # Location
    warehouse_id = fields.Many2one('wms.warehouse', string='Warehouse', required=True,
                                  default=lambda self: self.env['wms.warehouse'].search([], limit=1),
                                  tracking=True, states={'done': [('readonly', True)]})
    location_id = fields.Many2one('wms.location', string='Location', required=True,
                                 domain="[('warehouse_id', '=', warehouse_id)]",
                                 tracking=True, states={'done': [('readonly', True)]})
    
    # Batch/Lot
    lot_id = fields.Many2one('stock.lot', string='Lot/Serial',
                            domain="[('product_id', '=', product_id)]",
                            tracking=True)
    
    # Origin
    reason = fields.Selection([
        ('partial_receipt', 'Partial Receipt'),
        ('partial_delivery', 'Partial Delivery'),
        ('damaged', 'Damaged Items'),
        ('repacking', 'Repacking'),
        ('return', 'Customer Return'),
        ('other', 'Other'),
    ], string='Reason', required=True, default='other', tracking=True,
       states={'done': [('readonly', True)]})
    
    origin = fields.Char(string='Source Document', tracking=True,
                        states={'done': [('readonly', True)]})
    
    # Dates
    date = fields.Datetime(string='Date Identified', required=True, default=fields.Datetime.now,
                          tracking=True, states={'done': [('readonly', True)]})
    expiry_date = fields.Date(string='Expiry Date', help='Product expiry date if applicable')
    
    # Status
    state = fields.Selection([
        ('identified', 'Identified'),
        ('stored', 'Stored'),
        ('merged', 'Merged'),
        ('disposed', 'Disposed'),
    ], string='Status', default='identified', copy=False, tracking=True, index=True)
    
    # Linked quant
    quant_id = fields.Many2one('wms.stock.quant', string='Stock Quant', readonly=True,
                              help='Linked stock quant record')
    
    # Additional info
    user_id = fields.Many2one('res.users', string='Responsible', default=lambda self: self.env.user,
                             tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                default=lambda self: self.env.company)
    note = fields.Text(string='Notes')
    
    # Auto compute if is odd
    is_odd = fields.Boolean(string='Is Odd Item', compute='_compute_is_odd', store=True)

    @api.depends('quantity', 'standard_pack_qty')
    def _compute_percentage(self):
        for record in self:
            if record.standard_pack_qty > 0:
                record.percentage_of_standard = (record.quantity / record.standard_pack_qty) * 100
            else:
                record.percentage_of_standard = 0.0

    @api.depends('quantity', 'standard_pack_qty')
    def _compute_is_odd(self):
        """Auto-determine if item is odd (less than standard pack)"""
        for record in self:
            if record.standard_pack_qty > 0:
                record.is_odd = record.quantity < record.standard_pack_qty
            else:
                record.is_odd = False

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('stock.odd.item') or _('New')
        return super().create(vals)

    def action_mark_stored(self):
        """Mark as stored in odd item location"""
        for record in self:
            if record.state != 'identified':
                raise UserError(_('Only identified odd items can be marked as stored!'))
            
            # Check if location is designated odd item location
            if not record.location_id.is_odd_item_location:
                raise UserError(_(
                    'Location %s is not designated for odd items!\n'
                    'Please move to an odd item location first.'
                ) % record.location_id.complete_name)
            
            record.write({'state': 'stored'})
            record.message_post(body=_('Odd item stored in location %s') % record.location_id.complete_name)
        
        return True

    def action_create_merge_operation(self):
        """Open wizard to merge this odd item with others"""
        self.ensure_one()
        return {
            'name': _('Merge Odd Items'),
            'type': 'ir.actions.act_window',
            'res_model': 'odd.item.merge.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_product_id': self.product_id.id,
                'default_warehouse_id': self.warehouse_id.id,
                'default_odd_item_ids': [(6, 0, [self.id])],
            }
        }

    def action_dispose(self):
        """Mark as disposed"""
        for record in self:
            if record.state == 'merged':
                raise UserError(_('Cannot dispose merged items!'))
            record.write({'state': 'disposed'})
            record.message_post(body=_('Odd item disposed'))
        return True

    def action_reset_to_identified(self):
        """Reset to identified state"""
        for record in self:
            if record.state not in ['stored', 'disposed']:
                raise UserError(_('Cannot reset from current state!'))
            record.write({'state': 'identified'})
        return True

    @api.model
    def auto_identify_odd_items(self):
        """Scheduled action to auto-identify odd items in inventory"""
        # Find quants with quantity less than standard pack
        quants = self.env['wms.stock.quant'].search([
            ('quantity', '>', 0),
            ('product_id.standard_pack_qty', '>', 0),
            ('is_odd', '=', False),  # Not yet marked as odd
        ])
        
        odd_count = 0
        for quant in quants:
            if quant.quantity < quant.product_id.standard_pack_qty:
                # Check if odd item already exists
                existing = self.search([
                    ('quant_id', '=', quant.id),
                    ('state', 'not in', ['disposed']),
                ], limit=1)
                
                if not existing:
                    # Create odd item record
                    self.create({
                        'product_id': quant.product_id.id,
                        'quantity': quant.quantity,
                        'warehouse_id': quant.warehouse_id.id,
                        'location_id': quant.location_id.id,
                        'lot_id': quant.lot_id.id if quant.lot_id else False,
                        'reason': 'other',
                        'quant_id': quant.id,
                    })
                    
                    # Mark quant as odd
                    quant.write({'is_odd': True})
                    odd_count += 1
        
        return _('%d odd items auto-identified') % odd_count


class StockOddItemHistory(models.Model):
    _name = 'stock.odd.item.history'
    _description = 'Odd Item History'
    _order = 'date desc'

    odd_item_id = fields.Many2one('stock.odd.item', string='Odd Item', required=True, ondelete='cascade')
    date = fields.Datetime(string='Date', default=fields.Datetime.now, required=True)
    action = fields.Selection([
        ('identified', 'Identified'),
        ('moved', 'Moved'),
        ('merged', 'Merged'),
        ('adjusted', 'Quantity Adjusted'),
        ('disposed', 'Disposed'),
    ], string='Action', required=True)
    
    quantity_before = fields.Float(string='Qty Before', digits='Product Unit of Measure')
    quantity_after = fields.Float(string='Qty After', digits='Product Unit of Measure')
    location_before_id = fields.Many2one('wms.location', string='Location Before')
    location_after_id = fields.Many2one('wms.location', string='Location After')
    
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user)
    note = fields.Text(string='Notes')
