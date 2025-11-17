# -*- coding: utf-8 -*-
{
    'name': 'HDI HR Management',
    'version': '18.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Quản lý nhân sự HDI - Tuyển dụng, Đào tạo, Đánh giá, Chấm công',
    'description': """
        HDI Human Resources Management System
        =====================================
        
        Tính năng chính:
        - Quản lý hồ sơ nhân viên (kế thừa từ NGSD/NGSC)
        - Chấm công và quản lý ca làm việc
        - Quản lý nghỉ phép, tăng ca
        - Tuyển dụng và onboarding
        - Đào tạo và phát triển nhân viên
        - Đánh giá hiệu suất (KPI, OKR)
        - Quản lý năng lực và kỹ năng
        - Lương thưởng cơ bản
        - Báo cáo và phân tích HR
        
        Tích hợp:
        - Dựa trên code base NGSD/NGSC
        - Tương thích Odoo 18
    """,
    'author': 'HDI Development Team',
    'website': 'https://hdi.com.vn',
    'license': 'LGPL-3',
    
    'depends': [
        'base',
        'hr',
        'hr_holidays',
        'hr_attendance',
        'hr_contract',
        'hr_recruitment',
        'mail',
    ],
    
    'data': [
        # Security
        'security/hdi_hr_security.xml',
        'security/ir.model.access.csv',
        
        # Data
        'data/ir_sequence.xml',
        'data/hr_department_data.xml',
        'data/hr_job_data.xml',
        'data/hr_skill_data.xml',
        
        # Views - Employee
        'views/hr_employee_views.xml',
        'views/hr_department_views.xml',
        'views/hr_job_views.xml',
        
        # Views - Attendance
        'views/hr_attendance_views.xml',
        'views/hr_attendance_my_views.xml',
        'views/hr_leave_views.xml',
        
        # Views - Recruitment
        'views/hr_applicant_views.xml',
        
        # Views - Skills & Competency
        'views/hr_skill_views.xml',
        'views/hr_employee_skill_views.xml',
        
        # Views - Performance
        'views/hr_evaluation_views.xml',
        
        # Views - Configuration
        'views/res_config_settings_views.xml',
        
        # Wizards
        'wizard/hr_employee_onboarding_wizard_views.xml',
        'wizard/hr_attendance_checkin_wizard_views.xml',
        
        # Reports
        'report/hr_employee_report_templates.xml',
        
        # Menu
        'views/hdi_hr_menu.xml',
    ],
    
    'demo': [],
    
    'assets': {
        'web.assets_backend': [
            'hdi_hr/static/src/css/hdi_hr.css',
            'hdi_hr/static/src/js/hdi_hr_dashboard.js',
        ],
    },
    
    'images': ['static/description/icon.png'],
    
    'installable': True,
    'application': True,
    'auto_install': False,
}
