# -*- coding: utf-8 -*-

{
    'name': "ngsc_reporting",

    'summary': """Module Báo cáo""",

    'description': """
        Module báo cáo NGSC
    """,

    'author': "NGSC-DEVELOPER-TEAMS",
    'license': 'LGPL-3',
    'website': "http://ngsc.com.vn",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Base',
    'version': '18.0.1.0.0',

    # any module necessary for this one to work correctly
    'depends': ['ngsd_base', 'web', 'account_reports'],
    # always loaded
    'data': [
        # data

        # security
        'security/ir.model.access.csv',

        # wizard

        # views
        'views/norm_setting.xml',
        'views/report_weekly_by_project.xml',
        'views/project_quality_monthly_dashboard_actions.xml',
        'views/monthly_detailed_quality_report.xml',
        'views/final_project_completion_quality_report.xml',
        'views/project_quality_cron.xml',

        # menus
        'views/menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ngsc_reporting/static/src/js/**.js',
            'ngsc_reporting/static/src/scss/**.scss',
            'ngsc_reporting/static/src/lib/**.js',
        ],
        'web.assets_qweb': [
            'ngsc_reporting/static/src/xml/**/*',
        ],
    },
    # only loaded in demonstration mode
    'demo': [
    ],
    'application': True,
    'post_init_hook': 'run_first_quality_report',
    'installable': True,
}