# -*- coding: utf-8 -*-
{
    'name': 'HDI HR Attendance Enhanced',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Attendances',
    'summary': 'Hệ thống chấm công nâng cao với GPS, Queue, Offline mode',
    'description': """
        HDI HR Attendance Enhanced
        ==========================
        
        Module chấm công hoàn chỉnh kế thừa từ Odoo 18 core, kết hợp:
        
        **Từ NGSD:**
        - ✅ Dropdown chọn địa điểm làm việc
        - ✅ GPS Geolocation tự động
        - ✅ Hiển thị địa chỉ chấm công chi tiết
        - ✅ Kiểm tra khoảng cách với văn phòng
        - ✅ Tính toán giờ đi muộn/về sớm
        
        **Từ NGSC:**
        - ✅ Queue system xử lý bất đồng bộ
        - ✅ Chống double-click (bấm 2 lần)
        - ✅ Offline mode với localStorage
        - ✅ Auto-sync khi online trở lại
        - ✅ Workflow phê duyệt chấm công
        
        **Giao diện:**
        - ✅ Kiosk mode đẹp mắt
        - ✅ "Xin chào!" với avatar
        - ✅ Icon lớn "Bấm vào check in"
        - ✅ Responsive, thân thiện mobile
        
        **Báo cáo:**
        - ✅ Báo cáo chấm công theo địa điểm
        - ✅ Lịch sử GPS tracking
        - ✅ Dashboard thống kê
    """,
    'author': 'HDI Development Team',
    'website': 'https://hdi.com.vn',
    'license': 'LGPL-3',
    
    'depends': [
        'hr_attendance',      # Odoo 18 core
        'hdi_hr',            # HDI base HR module
    ],
    
    'external_dependencies': {
        'python': ['geopy'],
    },
    
    'data': [
        # Security
        'security/ir.model.access.csv',
        'security/security.xml',
        
        # Data
        'data/ir_config_parameter.xml',
        'data/ir_cron.xml',
        
        # Views
        'views/hr_work_location_views.xml',
        'views/hr_attendance_views.xml',
        'views/hr_attendance_log_views.xml',
        'views/menu.xml',
        
        # Wizard
        'wizard/attendance_checkin_wizard_views.xml',
    ],
    
    'demo': [
        'data/demo_data.xml',
    ],
    
    'assets': {
        'web.assets_backend': [
            'hdi_hr_attendance_enhanced/static/src/js/**/*.js',
            'hdi_hr_attendance_enhanced/static/src/xml/**/*.xml',
            'hdi_hr_attendance_enhanced/static/src/css/**/*.css',
        ],
    },
    
    'installable': True,
    'application': False,
    'auto_install': False,
}
