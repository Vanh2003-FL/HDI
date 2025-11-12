# -*- coding: utf-8 -*-
{
    'name': "Quản lý WBS phân cấp",
    'summary': """Quản lý WBS phân cấp""",
    'description': """Quản lý WBS phân cấp""",
    'author': "NGSC-DEVELOPER-TEAMS",
    'website': "http://ngsc.com.vn",
    'category': 'Project',
    'version': '0.1',
    'depends': ['ngsd_base', 'ngsc_project', 'ngsc_operational_support_ticket'],
    'data': [
        # data
        'data/mail_template.xml',
        'views/wizard_manual_wbs_run_view.xml',
        'data/ir_cron.xml',
        # security
        'security/ir.model.access.csv',
        'security/security.xml',
        # wizard
        # views
        'views/en_wbs_views.xml',
        'views/project_task_views.xml',
        'views/en_resource_planning_views.xml',
        'views/helpdesk_ticket_views.xml',
        'views/extend_import_js_file.xml',
        'views/project_task_import_wizard.xml',
        'views/nonproject_task.xml',
        'views/en_resource_detail.xml',
        'views/account_analytic_line.xml',
        'views/wbs_form_inherit_button.xml',
        # menus
    ],
    'assets': {
        'web.assets_qweb': [
            "ngsc_project_wbs/static/src/xml/**/*",
        ],
        'web.assets_backend': [
            "ngsc_project_wbs/static/src/js/*.js",
            "ngsc_project_wbs/static/src/css/*.css",
        ],
    },
    'demo': [
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
