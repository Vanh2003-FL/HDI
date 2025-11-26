{
    'name': 'WMS Transfer',
    'version': '18.0.1.0.0',
    'category': 'Inventory/WMS',
    'summary': 'Internal Stock Transfer Between Locations',
    'description': """
        WMS Transfer Module
        ===================
        * Internal location-to-location transfers
        * Approval workflow for transfers
        * Bulk transfer operations
        * Transfer reasons (replenishment, reorganization, damage)
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
        'views/wms_transfer_views.xml',
        'views/wms_transfer_menu.xml',
        'wizard/bulk_transfer_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
