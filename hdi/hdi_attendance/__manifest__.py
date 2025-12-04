# -*- coding: utf-8 -*-
{
    'name': 'HDI Attendance Management',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Attendances',
    'summary': 'HDI Attendance System - Check In/Out with GPS & Explanation',
    'description': """
    Module quản lý chấm công HDI với GPS và giải trình
    """,
    'author': 'HDI Development Team',
    'website': 'https://hdi.com.vn',
    'license': 'LGPL-3',

    'depends': [
        'base',
        'hr',
        'hr_attendance',
        'hdi_hr',
        'hdi_hr_attendance_geolocation',
    ],

    'data': [
        # Security
        'security/hdi_attendance_groups.xml',
        'security/ir.model.access.csv',

        # Data
        'data/sequence_data.xml',
        'data/system_parameter_data.xml',
        'data/submission_type_data.xml',
        'data/ir_cron_attendance_log.xml',

        'views/submission_type_views.xml',
        'views/attendance_dashboard.xml',
        'views/hr_attendance_views.xml',
        'views/hr_work_location_views.xml',
        'views/hr_attendance_explanation_detail_views.xml',
        'views/hr_attendance_explanation_approver_views.xml',
        'views/hr_attendance_explanation_views.xml',
        'views/hr_attendance_log_views.xml',
        'views/res_config_settings_views.xml',

        # Wizard
        'wizard/reason_for_refuse_wizard_views.xml',

        # Menu
        'views/hdi_attendance_menu.xml',
    ],

    'assets': {
        'web.assets_backend': [
            'hdi_attendance/static/src/js/hr_attendance_block_click.js',
            'hdi_attendance/static/src/components/attendance_dashboard/attendance_dashboard.js',
            'hdi_attendance/static/src/components/attendance_dashboard/attendance_dashboard.xml',
            'hdi_attendance/static/src/components/attendance_dashboard/attendance_dashboard.scss',
        ],
    },

    'images': ['static/description/icon.png'],

    'installable': True,
    'application': True,
    'auto_install': False,
}
