# -*- coding: utf-8 -*-
{
    'name': 'WMS Inventory Management',
    'version': '18.0.1.0.0',
    'category': 'Warehouse',
    'summary': 'Real-time Stock Tracking - Lot/Serial, FIFO/FEFO, Stock Movements',
    'description': """
        WMS Inventory Management
        ========================
        * Real-time stock quantities by location
        * Lot and serial number tracking
        * FIFO/FEFO/LIFO strategies
        * Stock movements with full traceability
        * Reservation management
        * Stock valuation by location
    """,
    'author': 'Your Company',
    'depends': [
        'wms_location',
        'stock',
        'product',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/wms_stock_quant_views.xml',
        'views/wms_stock_move_views.xml',
        'views/wms_inventory_menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
