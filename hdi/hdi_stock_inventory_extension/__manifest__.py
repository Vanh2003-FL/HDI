{
    'name': 'HDI Stock Inventory Extension',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Kiểm kê nâng cao (cycle count, batch count)',
    'author': 'HDI',
    'depends': ['stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_inventory_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
