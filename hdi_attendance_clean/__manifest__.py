# -*- coding: utf-8 -*-
{
    'name': 'HDI Attendance',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Attendances',
    'summary': 'Quản lý chấm công HDI với GPS tracking',
    'description': """
        HDI Attendance Management
        =========================
        - Inherit và customize hr_attendance module
        - GPS tracking khi check-in/check-out
        - Work location management
        - Kiosk mode với location selector
    """,
    'author': 'HDI Team',
    'depends': ['hr_attendance', 'mail'],
    'data': [
        'security/attendance_security.xml',
        'security/ir.model.access.csv',
        'views/work_location_views.xml',
        'views/attendance_views.xml',
        'views/menu_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hdi_attendance_clean/static/src/js/**/*',
            'hdi_attendance_clean/static/src/xml/**/*',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
