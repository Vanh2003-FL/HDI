{
    'name': 'WMS Integration',
    'version': '18.0.1.0.0',
    'category': 'Warehouse',
    'summary': 'REST API, Barcode Scanner, EDI Integration for WMS',
    'description': """
        WMS Integration Module
        ======================
        * REST API endpoints for external systems
        * Barcode scanner integration for mobile devices
        * EDI file import/export (XML, CSV, JSON)
        * Webhook notifications for key events
        * Third-party logistics carrier integration
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'wms_inventory',
        'wms_receipt',
        'wms_delivery',
        'wms_transfer',
        'wms_adjustment',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/wms_api_key_views.xml',
        'views/wms_api_log_views.xml',
        'views/wms_barcode_scan_views.xml',
        'views/wms_barcode_rule_views.xml',
        'views/wms_webhook_views.xml',
        'views/edi_import_wizard_views.xml',
        'views/edi_export_wizard_views.xml',
        'views/wms_integration_menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
