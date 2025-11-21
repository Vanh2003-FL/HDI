# -*- coding: utf-8 -*-
{
    'name': "ngsc_project",
    'summary': """
        Quản lý dự án""",
    'description': """
        Quản lý dự án
    """,
    'author': "NGSC-DEVELOPER-TEAMS",
    'website': "http://ngsc.com.vn",
    'category': 'Project',
    'version': '18.0.1.0.0',
    'depends': ['ngsd_base', 'ngsd_menu', 'ngsc_reporting',],
    'data': [
        # data
        'data/mail_template_data.xml',
        'data/project_stage_data.xml',
        # security
        'security/security.xml',
        'security/ir.model.access.csv',

        # wizard
        'wizard/split_line_confirm_wizard.xml',
        'wizard/new_version_project_decision_wizard.xml',
        'wizard/reason_for_adjustment_wizard.xml',

        # views
        "views/project_wbs_views.xml",
        'views/project_resource_detail.xml',
        'views/project_project.xml',
        'views/project_decision.xml',
        'views/project_level_views.xml',
        'views/project_legal_entity_views.xml',
        'views/en_problem_views.xml',
        # menus
        'views/menu.xml',
    ],
    'assets': {
        'web.assets_qweb': [
            "ngsc_project/static/src/xml/**/*",
        ],
        'web.assets_backend': [
            "ngsc_project/static/src/js/*.js",
            "ngsc_project/static/src/css/*.css",
            "ngsc_project/static/src/scss/*.scss",
        ],
    },
    'demo': [
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
