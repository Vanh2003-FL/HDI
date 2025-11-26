# -*- coding: utf-8 -*-
{
    'name': 'HDI Logistics Partner',
    'version': '18.0.1.0.0',
    'category': 'Inventory/HDI',
    'summary': '3PL Integration with Viettel Post, GHN, J&T, Ninja Van',
    'description': """
        HDI Logistics Partner (3PL Integration)
        ========================================
        * Multi-carrier integration (Viettel Post, GHN, J&T, Ninja Van)
        * Rate calculation engine (weight/zone-based pricing)
        * Real-time shipment tracking
        * Automated label generation
        * POD (Proof of Delivery) tracking
        * COD (Cash on Delivery) management
        * SLA monitoring and reporting
        * Webhook integration for status updates
    """,
    'author': 'HDI Vietnam',
    'website': 'https://www.hdivietnam.com',
    'license': 'LGPL-3',
    'depends': [
        'wms_delivery',
        'wms_integration',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/logistics_carrier_data.xml',
        'views/logistics_partner_views.xml',
        'views/logistics_rate_views.xml',
        'views/logistics_tracking_views.xml',
        'views/wms_delivery_views.xml',
        'views/hdi_logistics_partner_menu.xml',
        'wizard/shipment_create_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
