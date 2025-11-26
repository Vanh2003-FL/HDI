# -*- coding: utf-8 -*-
{
    'name': 'HDI Fleet Assignment',
    'version': '18.0.1.0.0',
    'category': 'Inventory/HDI',
    'summary': 'Fleet Management & Vehicle Assignment with Route Optimization',
    'description': """
        HDI Fleet Assignment
        ====================
        * Vehicle assignment for deliveries
        * Route optimization algorithms
        * GPS tracking integration
        * Driver mobile app integration
        * Fuel consumption tracking
        * Vehicle maintenance scheduling
        * Delivery performance analytics
        * Real-time location updates
        * Geofencing alerts
    """,
    'author': 'HDI Vietnam',
    'website': 'https://www.hdivietnam.com',
    'license': 'LGPL-3',
    'depends': [
        'fleet',
        'wms_delivery',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/fleet_vehicle_views.xml',
        'views/picking_vehicle_assign_views.xml',
        'views/vehicle_route_plan_views.xml',
        'views/vehicle_gps_tracking_views.xml',
        'views/hdi_fleet_assignment_menu.xml',
        'wizard/route_optimize_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
