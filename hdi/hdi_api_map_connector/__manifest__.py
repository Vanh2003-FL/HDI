{
    'name': 'HDI API Map Connector',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Kết nối Odoo WMS ↔ Digital Layout 3D',
    'author': 'HDI',
    'depends': ['stock', 'hdi_stock_putaway_map'],
    'data': [
        'security/ir.model.access.csv',
        'views/map_sync_queue_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
