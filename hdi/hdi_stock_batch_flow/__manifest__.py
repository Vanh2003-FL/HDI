# -*- coding: utf-8 -*-
{
    'name': 'HDI Stock Batch Flow',
    'version': '18.0.1.0.0',
    'category': 'Inventory/HDI',
    'summary': 'Batch Split and Merge Operations for WMS',
    'description': """
        HDI Stock Batch Flow Management
        ================================
        * Split large batches into smaller batches
        * Merge multiple small batches into one batch
        * QR code generation for batch tracking
        * Pallet/Container breakdown support
        * Full audit trail and traceability
        * Integration with WMS inventory system
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
        'views/stock_batch_split_views.xml',
        'views/stock_batch_merge_views.xml',
        'views/hdi_stock_batch_menu.xml',
        'wizard/batch_split_wizard_views.xml',
        'wizard/batch_merge_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
