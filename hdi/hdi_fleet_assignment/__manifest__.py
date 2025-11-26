{
    'name': 'HDI Fleet Assignment',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Delivery',
    'summary': 'Quản lý đội xe + phân công giao hàng',
    'author': 'HDI',
    'depends': ['stock', 'fleet'],
    'data': [
        'security/ir.model.access.csv',
        'views/picking_vehicle_assign_views.xml',
        'views/stock_picking_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
