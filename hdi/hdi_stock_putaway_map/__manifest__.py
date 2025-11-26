{
    'name': 'HDI Stock Putaway Map',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Quản lý bản đồ kho 3D + gợi ý vị trí',
    'description': """
        HDI Stock Putaway Map Management
        =================================
        * Chuẩn hóa vị trí kho theo: Tầng → Dãy → Kệ → Ô
        * Hiển thị bản đồ kho 3D (X, Y, Z)
        * Engine gợi ý vị trí đặt hàng theo rule ABC/FIFO/khoảng cách
        * Tối ưu hóa không gian kho
    """,
    'author': 'HDI',
    'website': 'https://www.hdi.com',
    'depends': ['stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_location_views.xml',
        'views/putaway_suggestion_views.xml',
        'views/product_template_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
