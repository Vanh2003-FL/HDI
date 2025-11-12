# -*- coding: utf-8 -*-
{
    'name': 'Đánh giá hiệu suất nhân viên',
    'version': '1.0',
    'category': 'HR',
    'sequence': 100,
    'summary': 'Đánh giá hiệu suất nhân viên',
    'description': "",
    'author': "NGSC-DEVELOPER-TEAMS",
    'website': "http://ngsc.com.vn",
    'depends': ['ngsd_base', 'ngsc_project_wbs', 'ngsc_utils', 'ngsc_hr_unit_hierarchy', 'ngsc_nonproject_resource'],
    'data': [
        'data/ir_cron.xml',
        'data/mail_template.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
        'wizard/remind_evaluation_wizard_views.xml',
        'wizard/performance_evaluation_exclude_wizard_views.xml',
        'views/project_task_views.xml',
        'views/en_nonproject_task_views.xml',
        'views/hr_performance_evaluation_exclude_views.xml',
        'views/hr_performance_evaluation_views.xml',
        'views/performance_evaluation_report.xml',
        'views/task_evaluation_views.xml',
        'views/hr_department_views.xml',
        'views/menus.xml'
    ],
    'demo': [
    ],
    'css': [
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'assets': {
        'web.assets_qweb': [
            'ngsc_performance_evaluation/static/src/xml/**/*',
        ],
        'web.assets_backend': [
            "ngsc_performance_evaluation/static/src/js/*.js",
            "ngsc_performance_evaluation/static/src/css/*.css",
        ],
    },
    'license': 'LGPL-3',
}
