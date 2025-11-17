# -*- coding: utf-8 -*-
{
    'name': 'HDI Attendance Management',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Attendances',
    'summary': 'Hệ thống chấm công HDI - Quản lý chấm công nâng cao',
    'description': """
        HDI Attendance Management System
        ================================
        
        Tính năng chính:
        - Chấm công check-in/check-out với GPS
        - Quản lý ca làm việc linh hoạt
        - Theo dõi giờ làm việc và tăng ca
        - Quản lý địa điểm làm việc
        - Cảnh báo đi muộn, về sớm
        - Giải trình chấm công
        - Dashboard theo dõi chấm công
        - Báo cáo chấm công chi tiết
        - Tích hợp với timesheet
        - Thông báo tự động
        - Kiểm soát qua địa điểm
        
        Tích hợp:
        - Kế thừa từ NGSD/NGSC modules
        - Tương thích Odoo 18
        - Hỗ trợ multiple work locations
        - API cho mobile app
    """,
    'author': 'HDI Development Team',
    'website': 'https://hdi.com.vn',
    'license': 'LGPL-3',
    
    'depends': [
        'base',
        'hr',
        'hr_attendance',
        'hr_holidays',
        'mail',
        'resource',
        'web',
    ],
    
    'data': [
        # Security
        'security/hdi_attendance_security.xml',
        'security/ir.model.access.csv',
        
        # Data
        'data/ir_sequence.xml',
        'data/hr_work_location_data.xml',
        'data/attendance_settings_data.xml',
        
        # Views - Core Models
        'views/hr_attendance_views.xml',
        # 'views/hr_attendance_calendar_views.xml',
        # 'views/hr_attendance_my_views.xml',
        'views/hr_work_location_views.xml',
        # 'views/hr_employee_views.xml',
        
        # Views - Configuration
        'views/attendance_settings_views.xml',
        'views/attendance_exception_views.xml',
        'views/res_config_settings_views.xml',
        
        # Wizards
        'wizard/attendance_checkin_wizard_views.xml',
        'wizard/attendance_explanation_wizard_views.xml',
        # 'wizard/attendance_report_wizard_views.xml',
        # 'wizard/attendance_bulk_update_wizard_views.xml',
        
        # Reports
        # 'report/attendance_report_templates.xml',
        # 'report/attendance_summary_report.xml',
        
        # Menu
        'views/hdi_attendance_menu.xml',
    ],
    
    'demo': [
        # 'demo/hr_work_location_demo.xml',
        # 'demo/hr_attendance_demo.xml',
    ],
    
    'assets': {
        'web.assets_backend': [
            'hdi_attendance/static/src/css/hdi_attendance.css',
            'hdi_attendance/static/src/js/attendance_dashboard.js',
            'hdi_attendance/static/src/js/attendance_kiosk.js',
        ],
        'web.assets_qweb': [
            'hdi_attendance/static/src/xml/attendance_templates.xml',
        ],
    },
    
    'images': ['static/description/icon.png'],
    
    'installable': True,
    'application': True,
    'auto_install': False,
    'sequence': 95,
}