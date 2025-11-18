# -*- coding: utf-8 -*-
{
    'name': 'HDI Attendance',
    'version': '18.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Quản lý chấm công HDI',
    'description': """
        HDI Attendance Management
        =========================
        Quản lý chấm công với GPS tracking và work location
    """,
    'author': 'HDI Team',
    'depends': ['base', 'hr', 'mail'],
    'data': [
        'security/attendance_security.xml',
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'views/attendance_views.xml',
        'views/work_location_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
