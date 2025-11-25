# -*- coding: utf-8 -*-
{
    'name': 'HDI Attendance Management',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Attendances',
    'summary': 'HDI Attendance System - Check In/Out with GPS & Explanation',
    'description': """
        HDI Attendance Management System
        ==================================
        
        Hệ thống chấm công HDI dựa trên kiến trúc NGSC/NGSD:
        
        🎯 TÍNH NĂNG CHÍNH:
        - ✅ Check In/Out Interface (Giao diện chấm công)
        - ✅ My Attendance (Chấm công của tôi)
        - ✅ Attendance Explanation System (Giải trình chấm công)
        - ✅ GPS Geolocation Support (Hỗ trợ định vị GPS)
        - ✅ Async Attendance Logging (Chấm công bất đồng bộ)
        - ✅ Prevent Double Click (Chống bấm nút 2 lần)
        - ✅ Work Location Management (Quản lý địa điểm làm việc)
        - ✅ Attendance Reports (Báo cáo chấm công)
        
        🔧 TÍCH HỢP:
        - Kế thừa từ NGSD ngs_attendance
        - Kế thừa từ NGSC ngs_hr_attendance_async
        - Tương thích Odoo 18
        - Tích hợp với hdi_hr
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
        
        # Views
        'views/attendance_dashboard.xml',
        'views/hr_attendance_views.xml',
        'views/hr_attendance_explanation_detail_views.xml',
        'views/hr_attendance_explanation_approver_views.xml',
        'views/hr_attendance_explanation_views.xml',
        'views/submission_type_views.xml',
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
