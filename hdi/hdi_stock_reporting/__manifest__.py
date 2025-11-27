{
    'name': 'HDI Stock Reporting',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Báo cáo WMS (nhập – xuất – tồn – kiểm kê)',
    'author': 'HDI',
    'depends': ['stock', 'hdi_stock_batch_flow', 'hdi_stock_putaway_map'],
    'data': [
        'security/ir.model.access.csv',
        # 'views/stock_report_entry_views.xml',  # TODO: Create this file
        'views/menu_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
