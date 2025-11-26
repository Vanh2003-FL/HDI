# -*- coding: utf-8 -*-

from odoo import models, fields


class WmsAdjustmentReason(models.Model):
    _name = 'wms.adjustment.reason'
    _description = 'WMS Adjustment Reason'
    _order = 'sequence, name'

    name = fields.Char(
        string='Reason',
        required=True,
        translate=True
    )
    
    code = fields.Char(
        string='Code',
        required=True
    )
    
    adjustment_type = fields.Selection([
        ('increase', 'Increase Stock'),
        ('decrease', 'Decrease Stock'),
        ('cycle_count', 'Cycle Count'),
        ('physical', 'Physical Inventory'),
        ('correction', 'Correction')
    ], string='Adjustment Type', required=True)
    
    sequence = fields.Integer(
        string='Sequence',
        default=10
    )
    
    active = fields.Boolean(
        string='Active',
        default=True
    )
    
    description = fields.Text(
        string='Description'
    )

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Reason code must be unique.')
    ]
