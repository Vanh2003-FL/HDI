# -*- coding: utf-8 -*-
{
    'name': 'Kế hoạch nguồn lực ngoài dự án',
    'version': '18.0.1.0.0',
    'category': 'Project',
    'sequence': 200,
    'summary': 'Kế hoạch nguồn lực ngoài dự án',
    'description': "Kế hoạch nguồn lực ngoài dự án",
    'author': "NGSC-DEVELOPER-TEAMS",
    'website': "http://ngsc.com.vn",
    'depends': ['ngsd_base', 'ngsc_utils', 'account_reports'],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'data/ir_cron.xml',
        'wizard/nonproject_resource_planning_wizard_views.xml',
        'views/en_nonproject_task_views.xml',
        'views/res_config_settings_views.xml',
        'views/nonproject_resource_planning_exclude_views.xml',
        'views/nonproject_resource_planning_views.xml',
        'report/resource_nonproject_account_report_views.xml',
        'views/menus.xml'
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'assets': {
        'web.assets_qweb': [
            'ngsc_nonproject_resource/static/src/xml/**/*',
        ],
        'web.assets_backend': [
            "ngsc_nonproject_resource/static/src/js/*.js",
            "ngsc_nonproject_resource/static/src/css/*.css",
        ],
    },
    'license': 'LGPL-3',
}
