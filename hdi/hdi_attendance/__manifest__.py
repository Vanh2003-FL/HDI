# -*- coding: utf-8 -*-
{
    'name': 'HDI Attendance Management',
    'version': '18.0.2.0.0',
    'category': 'Human Resources/Attendances',
    'summary': 'HDI Attendance System - Complete NGSC/NGSD Implementation',
    'description': """
        HDI Attendance Management System
        ==================================
        
        🎯 TÍNH NĂNG CHÍNH:
        - ✅ Check In/Out Dashboard với GPS
        - ✅ Explanation Workflow (Multi-level Approval)
        - ✅ Detail Lines cho time adjustment
        - ✅ Async Attendance Logging (Anti-duplicate)
        - ✅ Auto Detection: Late/Early/Missing
        - ✅ Color-coded List Views
        - ✅ Approval Flow Management
        - ✅ Timesheet Integration
        - ✅ Auto Checkout Cron
        - ✅ Notification System
        
        🔧 WIZARDS:
        - Reason for Refuse
        - Task Timesheet Explanation
        - Report Timekeeping (PDF/XLSX/DOCX)
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
        'data/ir_cron_attendance_log.xml',
        'data/submission_type_data.xml',
        
        # Views
        'views/attendance_dashboard.xml',
        'views/hr_attendance_views.xml',
        'views/hr_attendance_explanation_views.xml',
        'views/hr_attendance_log_views.xml',
        'views/submission_type_views.xml',
        
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
