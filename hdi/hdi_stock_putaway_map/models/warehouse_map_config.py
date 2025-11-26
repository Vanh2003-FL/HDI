# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class WarehouseMapConfig(models.Model):
    _name = 'warehouse.map.config'
    _description = 'Warehouse Map Configuration'

    name = fields.Char(string='Map Name', required=True)
    warehouse_id = fields.Many2one('wms.warehouse', string='Warehouse', required=True)
    
    # Map dimensions
    map_width = fields.Float(string='Map Width (m)', default=100.0, required=True)
    map_height = fields.Float(string='Map Height (m)', default=50.0, required=True)
    grid_size = fields.Float(string='Grid Size (m)', default=1.0,
                            help='Grid cell size for rendering')
    
    # Visualization settings
    show_capacity_heatmap = fields.Boolean(string='Show Capacity Heatmap', default=True)
    show_abc_zones = fields.Boolean(string='Show ABC Zones', default=True)
    show_location_labels = fields.Boolean(string='Show Location Labels', default=True)
    
    # Color schemes for capacity
    color_empty = fields.Char(string='Color Empty (<30%)', default='#2ecc71')
    color_medium = fields.Char(string='Color Medium (30-70%)', default='#f39c12')
    color_full = fields.Char(string='Color Full (>70%)', default='#e74c3c')
    
    # Highlight location
    highlight_location_id = fields.Many2one('wms.location', string='Highlight Location')
    
    # Map data (computed)
    location_data = fields.Text(string='Location JSON Data', compute='_compute_map_data')
    
    @api.depends('warehouse_id', 'highlight_location_id')
    def _compute_map_data(self):
        """Generate JSON data for map rendering"""
        import json
        
        for record in self:
            if not record.warehouse_id:
                record.location_data = '{}'
                continue
            
            locations = self.env['wms.location'].search([
                ('warehouse_id', '=', record.warehouse_id.id),
                ('x_coordinate', '!=', 0),
                ('y_coordinate', '!=', 0),
            ])
            
            data = []
            for loc in locations:
                # Determine color based on capacity
                if loc.capacity_percentage < 30:
                    color = record.color_empty
                elif loc.capacity_percentage < 70:
                    color = record.color_medium
                else:
                    color = record.color_full
                
                data.append({
                    'id': loc.id,
                    'name': loc.complete_name,
                    'address': loc.location_address or loc.name,
                    'x': loc.x_coordinate,
                    'y': loc.y_coordinate,
                    'z': loc.z_coordinate or 0,
                    'capacity': loc.capacity,
                    'available': loc.available_capacity,
                    'percentage': loc.capacity_percentage,
                    'abc_zone': loc.abc_zone or '',
                    'color': color,
                    'highlighted': loc.id == record.highlight_location_id.id,
                })
            
            record.location_data = json.dumps(data)

    def action_view_map(self):
        """Open map view"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Warehouse Map - %s') % self.warehouse_id.name,
            'res_model': 'warehouse.map.config',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'fullscreen',
        }


class WarehouseMapLayer(models.Model):
    _name = 'warehouse.map.layer'
    _description = 'Warehouse Map Layer'
    _order = 'sequence'

    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(string='Layer Name', required=True)
    map_config_id = fields.Many2one('warehouse.map.config', string='Map Config', required=True)
    
    layer_type = fields.Selection([
        ('zones', 'Zones'),
        ('locations', 'Locations'),
        ('aisles', 'Aisles'),
        ('equipment', 'Equipment'),
    ], string='Layer Type', required=True)
    
    visible = fields.Boolean(string='Visible', default=True)
    opacity = fields.Float(string='Opacity', default=1.0, help='0.0 to 1.0')
