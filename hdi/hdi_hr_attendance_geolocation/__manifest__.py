# -*- coding: utf-8 -*-
{
    'name': 'HDI HR Attendance Geolocation',
    'version': '18.0.1.0.0',
    'category': 'hdi',
    'summary': 'Chấm công với định vị địa lý GPS',
    'description': """
        HDI HR Attendance Geolocation
    """,
    'author': 'HDI Development Team',
    'website': 'https://hditech.com.vn',
    'license': 'LGPL-3',
    
    'depends': [
        'hr_attendance',
        'hdi_hr',
    ],
    
    'external_dependencies': {
        'python': ['geopy'],
    },
    
    'data': [
        'security/ir.model.access.csv',
        # 'data/location_data.xml',  # Removed: address_id required in Odoo 18
        'data/ir_config_parameter.xml',
        'views/hr_attendance_views.xml',
        'views/hr_work_location_views.xml',
        # 'views/res_config_settings_views.xml',  # Removed: XPath issues in Odoo 18
        'views/menu.xml',
    ],
    
    'assets': {
        'web.assets_backend': [
            'hdi_hr_attendance_geolocation/static/src/js/attendance_geolocation.js',
            'hdi_hr_attendance_geolocation/static/src/css/attendance_geolocation.css',
        ],
    },
    
    'installable': True,
    'application': False,
    'auto_install': False,
}
