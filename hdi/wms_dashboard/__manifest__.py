{
    'name': 'WMS Dashboard',
    'version': '18.0.1.0.0',
    'category': 'Inventory/WMS',
    'summary': 'WMS Real-time Dashboard with KPIs',
    'description': """
        WMS Dashboard Module
        ====================
        * Real-time warehouse KPI dashboard
        * Stock level indicators
        * Capacity utilization charts
        * Pending operations counters
        * Movement trends (daily/weekly/monthly)
        * Low stock alerts
        * Expiring products alerts
        * Top products by movement
        * Performance metrics
    """,
    'author': 'HDI',
    'website': 'https://www.hdivietnam.com',
    'license': 'LGPL-3',
    'depends': [
        'wms_inventory',
        'wms_receipt',
        'wms_delivery',
        'wms_transfer',
        'wms_adjustment',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/wms_dashboard_views.xml',
        'views/wms_dashboard_menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'wms_dashboard/static/src/js/wms_dashboard.js',
            'wms_dashboard/static/src/xml/wms_dashboard.xml',
            'wms_dashboard/static/src/css/wms_dashboard.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
