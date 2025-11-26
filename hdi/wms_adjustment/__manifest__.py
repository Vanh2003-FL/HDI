{
    'name': 'WMS Adjustment',
    'version': '18.0.1.0.0',
    'category': 'Inventory/WMS',
    'summary': 'Inventory Adjustments and Cycle Counting',
    'description': """
        WMS Adjustment Module
        =====================
        * Inventory adjustments (increase/decrease stock)
        * Cycle counting with schedules
        * Physical inventory
        * Variance reporting and approval
        * Reason codes for adjustments
        * Integration with stock move system
    """,
    'author': 'HDI',
    'website': 'https://www.hdivietnam.com',
    'license': 'LGPL-3',
    'depends': [
        'wms_inventory',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/adjustment_reason_data.xml',
        'views/wms_adjustment_views.xml',
        'views/wms_adjustment_reason_views.xml',
        'views/wms_adjustment_menu.xml',
        'wizard/cycle_count_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
