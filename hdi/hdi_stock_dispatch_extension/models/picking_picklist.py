from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class PickingPicklist(models.Model):
    _name = 'picking.picklist'
    _description = 'Picking Picklist'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Picklist Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    picking_id = fields.Many2one(
        'stock.picking',
        string='Delivery Order',
        required=True,
        domain=[('picking_type_code', '=', 'outgoing')],
        tracking=True
    )
    picker_id = fields.Many2one(
        'res.users',
        string='Picker',
        tracking=True
    )
    picklist_date = fields.Datetime(
        string='Picklist Date',
        default=fields.Datetime.now,
        required=True
    )
    line_ids = fields.One2many(
        'picklist.line',
        'picklist_id',
        string='Picklist Lines'
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('assigned', 'Assigned'),
        ('in_progress', 'Picking'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ], string='Status', default='draft', tracking=True)
    
    # Staging
    staging_location_id = fields.Many2one(
        'stock.location',
        string='Staging Location',
        help='Temporary location before packing'
    )
    
    # Statistics
    total_lines = fields.Integer(
        compute='_compute_statistics',
        string='Total Lines'
    )
    picked_lines = fields.Integer(
        compute='_compute_statistics',
        string='Picked Lines'
    )
    progress = fields.Float(
        compute='_compute_statistics',
        string='Progress (%)'
    )
    
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company
    )

    @api.depends('line_ids', 'line_ids.picked_qty')
    def _compute_statistics(self):
        for record in self:
            record.total_lines = len(record.line_ids)
            record.picked_lines = len(record.line_ids.filtered(lambda l: l.is_picked))
            if record.total_lines:
                record.progress = (record.picked_lines / record.total_lines) * 100
            else:
                record.progress = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('picking.picklist') or _('New')
        return super().create(vals_list)

    def action_assign_picker(self):
        self.ensure_one()
        self.write({
            'state': 'assigned',
            'picker_id': self.env.user.id,
        })

    def action_start_picking(self):
        self.ensure_one()
        if not self.picker_id:
            self.picker_id = self.env.user.id
        self.state = 'in_progress'

    def action_done(self):
        self.ensure_one()
        if any(not line.is_picked for line in self.line_ids):
            raise UserError(_('All lines must be picked before completing.'))
        self.state = 'done'

    def action_cancel(self):
        self.ensure_one()
        self.state = 'cancel'
