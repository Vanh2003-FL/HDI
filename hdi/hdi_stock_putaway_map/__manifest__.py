# -*- coding: utf-8 -*-
{
    'name': 'HDI Stock Putaway Map',
    'version': '18.0.1.0.0',
    'category': 'Inventory/HDI',
    'summary': '3D Warehouse Mapping with XYZ Coordinates and Smart Putaway',
    'description': """
        HDI Stock Putaway Map
        =====================
        * 3D warehouse location addressing (Floor-Aisle-Rack-Bin)
        * XYZ coordinates for locations
        * Smart putaway suggestion engine
        * ABC classification-based suggestions
        * Distance optimization algorithms
        * Capacity-based location selection
        * Heatmap visualization of warehouse capacity
    """,
    'author': 'HDI Vietnam',
    'website': 'https://www.hdivietnam.com',
    'license': 'LGPL-3',
    'depends': [
        'wms_location',
        'wms_receipt',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/wms_location_views.xml',
        'views/putaway_suggestion_views.xml',
        'views/warehouse_map_config_views.xml',
        'views/hdi_stock_putaway_map_menu.xml',
        'wizard/smart_putaway_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
