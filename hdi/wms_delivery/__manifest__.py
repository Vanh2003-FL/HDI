# -*- coding: utf-8 -*-
{
    'name': 'WMS Delivery Management',
    'version': '18.0.1.0.0',
    'category': 'Warehouse',
    'summary': 'Outbound Operations - Picking, Packing, Shipping with Wave Management',
    'description': """
        WMS Delivery Management
        =======================
        * Delivery orders with picking waves
        * Multiple picking strategies (FIFO/FEFO/LIFO)
        * Batch picking support
        * Packing operations
        * Shipping label generation
        * Integration with sales orders
    """,
    'author': 'Your Company',
    'depends': [
        'wms_inventory',
        'sale',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/wms_delivery_views.xml',
        'views/wms_delivery_line_views.xml',
        'wizard/batch_picking_wizard_views.xml',
        'views/wms_delivery_menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
