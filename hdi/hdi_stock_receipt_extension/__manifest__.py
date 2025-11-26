{
    'name': 'HDI Stock Receipt Extension',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Mở rộng quy trình nhập kho với thông tin Container, HQ, QC',
    'description': """
        HDI Stock Receipt Extension
        ============================
        * Thông tin Container, Tờ khai HQ, Bill
        * Quản lý QC nhập kho
        * Tracking batch list chi tiết
        * Mở rộng Stock Picking Receipt
    """,
    'author': 'HDI',
    'website': 'https://www.hdi.com',
    'depends': ['stock', 'hdi_stock_batch_flow'],
    'data': [
        'data/ir_sequence_data.xml',
        'security/ir.model.access.csv',
        'views/stock_receipt_views.xml',
        'views/stock_picking_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
