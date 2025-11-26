{
    'name': 'HDI Logistics Partner',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Delivery',
    'summary': 'Quản lý đối tác vận chuyển (3PL)',
    'author': 'HDI',
    'depends': ['stock', 'delivery'],
    'data': [
        'security/ir.model.access.csv',
        'views/logistics_partner_views.xml',
        'views/logistics_rate_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
