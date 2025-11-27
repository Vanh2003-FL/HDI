{
    'name': 'HDI Stock Batch Flow',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Quản lý vòng đời batch/lô: tách – gộp – QR – tracking',
    'description': """
        HDI Stock Batch Flow Management
        ================================
        * Chia 1 lô lớn thành nhiều lô nhỏ (Batch Split)
        * Gộp nhiều lô nhỏ thành một lô lớn (Batch Merge)
        * Hỗ trợ QR code tracking
        * Quản lý vòng đời batch hoàn chỉnh
    """,
    'author': 'HDI',
    'website': 'https://www.hdi.com',
    'depends': ['stock', 'barcodes'],
    'data': [
        'data/ir_sequence_data.xml',
        'security/ir.model.access.csv',
        'views/stock_batch_split_views.xml',
        'views/stock_batch_merge_views.xml',
        'views/stock_lot_views.xml',
        # 'views/menu_views.xml',  # Menus already defined in view files
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
