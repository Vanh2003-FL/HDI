{
    'name': 'HDI Stock Dispatch Extension',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Quy trình xuất kho chuyên nghiệp (Picklist – Pack – Staging)',
    'author': 'HDI',
    'depends': ['stock', 'hdi_stock_batch_flow'],
    'data': [
        'data/ir_sequence_data.xml',
        'security/ir.model.access.csv',
        'views/picking_picklist_views.xml',
        'views/menu_views.xml',
        'wizard/generate_picklist_wizard_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
