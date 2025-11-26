{
    'name': 'HDI Barcode Workflow',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Quy trình quét barcode nhiều bước',
    'author': 'HDI',
    'depends': ['stock', 'barcodes'],
    'data': [
        'data/ir_sequence_data.xml',
        'security/ir.model.access.csv',
        'views/barcode_workflow_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
