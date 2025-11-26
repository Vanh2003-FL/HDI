# -*- coding: utf-8 -*-
{
    'name': 'HDI Stock Odd Items Management',
    'version': '18.0.1.0.0',
    'category': 'Inventory/HDI',
    'summary': 'Manage Odd Items, Remnants, and Partial Pallets',
    'description': """
        HDI Stock Odd Items Management
        ===============================
        * Track odd/remnant stock items
        * Manage partial pallets and broken cases
        * Automatic odd item detection
        * Merge odd items into standard packs
        * Dedicated odd item zone management
        * Integration with WMS inventory
    """,
    'author': 'HDI Vietnam',
    'website': 'https://www.hdivietnam.com',
    'license': 'LGPL-3',
    'depends': [
        'stock',
        'wms_inventory',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/stock_odd_item_views.xml',
        'views/wms_stock_quant_views.xml',
        'views/product_product_views.xml',
        'views/hdi_stock_odd_items_menu.xml',
        'wizard/odd_item_merge_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
