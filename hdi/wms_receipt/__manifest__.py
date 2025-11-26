# -*- coding: utf-8 -*-
{
    'name': 'WMS Receipt Management',
    'version': '18.0.1.0.0',
    'category': 'Warehouse',
    'summary': 'Inbound Operations - GRN, Quality Check, Putaway Strategy',
    'description': """
        WMS Receipt Management
        ======================
        * Goods Receipt Note (GRN)
        * Quality inspection workflow
        * Automatic putaway suggestions
        * Multiple putaway strategies (nearest, FIFO, fixed)
        * Barcode scanning support
        * Integration with purchase orders
    """,
    'author': 'Your Company',
    'depends': [
        'wms_inventory',
        'purchase',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/wms_receipt_views.xml',
        'views/wms_receipt_line_views.xml',
        'wizard/putaway_suggestion_wizard_views.xml',
        'views/wms_receipt_menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
