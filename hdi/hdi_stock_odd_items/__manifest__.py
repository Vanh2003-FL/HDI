{
    'name': 'HDI Stock Odd Items',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Quản lý hàng lẻ / thiếu lô',
    'author': 'HDI',
    'depends': ['stock'],
    'data': [
        'security/ir.model.access.csv',
        # 'views/odd_item_views.xml',  # TODO
        'views/barcode_item_views.xml',
        # 'views/stock_quant_views.xml',  # TODO
        'views/menu_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
