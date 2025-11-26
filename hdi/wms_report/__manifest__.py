{
    'name': 'WMS Report',
    'version': '18.0.1.0.0',
    'category': 'Inventory/WMS',
    'summary': 'WMS Advanced Reporting and Analytics',
    'description': """
        WMS Report Module
        =================
        * Stock aging report (by FIFO/FEFO dates)
        * ABC analysis (product classification by value)
        * Stock movement history report
        * Inventory valuation report
        * Location capacity utilization report
        * Excel export for all reports (xlsxwriter)
        * PDF export support
        * Customizable date ranges and filters
    """,
    'author': 'HDI',
    'website': 'https://www.hdivietnam.com',
    'license': 'LGPL-3',
    'depends': [
        'wms_inventory',
        'wms_receipt',
        'wms_delivery',
    ],
    'external_dependencies': {
        'python': ['xlsxwriter'],
    },
    'data': [
        'security/ir.model.access.csv',
        'wizard/stock_aging_report_wizard_views.xml',
        'wizard/abc_analysis_wizard_views.xml',
        'wizard/stock_movement_report_wizard_views.xml',
        'wizard/inventory_valuation_wizard_views.xml',
        'wizard/location_utilization_wizard_views.xml',
        'views/wms_report_menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
