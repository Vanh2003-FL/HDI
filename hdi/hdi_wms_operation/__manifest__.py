{
    'name': 'HDI WMS Operations',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Nghiệp vụ WMS: NK_NV, ĐC_NV, XK_BH, KK_NV',
    'description': """
        HDI WMS Operations - Nghiệp vụ chi tiết
        ========================================
        * NK_NV_01-04: 4 luồng nhập kho (Sản xuất, Xuất khẩu, Nhập khẩu, Chuyển kho)
        * ĐC_NV_01-02: Điều chuyển vị trí và Phân rã Batch
        * XK_BH_01: Xuất kho FIFO với picking list
        * KK_NV_01-02: Kiểm kê Batch và Barcode
        
        Workflow State Machine đầy đủ:
        - Batch: draft → scanned → placed → confirmed
        - Receipt: new → done → approved → transferred
        - Transfer: draft → waiting → in_progress → done → approved
        - Picking: draft → assigned → in_progress → done
        - Inventory: draft → in_progress → done → approved
    """,
    'author': 'HDI',
    'website': 'https://www.hdi.com',
    'depends': [
        'stock',
        'barcodes',
        'hdi_stock_batch_flow',
        'hdi_stock_putaway_map',
        'hdi_stock_receipt_extension',
        'hdi_stock_dispatch_extension',
    ],
    'data': [
        'data/ir_sequence_data.xml',
        'security/ir.model.access.csv',
        # Master Data
        'views/product_template_views.xml',
        'views/stock_lot_views.xml',
        # NK - Receipt Operations
        'views/receipt_operation_views.xml',
        # DC - Transfer Operations
        'views/transfer_operation_views.xml',
        # Barcode Items
        'views/barcode_item_views.xml',
        # Menus
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
