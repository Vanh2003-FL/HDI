# -*- coding: utf-8 -*-
{
    'name': "Chi phí sản xuất",
    'summary': """Chi phí sản xuất""",
    'description': """Chi phí sản xuất""",
    'author': "NGSC-DEVELOPER-TEAMS",
    'website': "http://ngsc.com.vn",
    'category': 'Project',
    'version': '0.1',
    'depends': ['ngsd_base', 'ngsc_project_wbs'],
    'data': [
        # data
        # security
        'security/ir.model.access.csv',

        # wizard
        # views
        'views/en_name_level_views.xml',
        'views/en_resource_planning_views.xml',
        'views/hr_employee_views.xml',
        'views/project_project_views.xml',
        'views/project_task_views.xml',
        'views/project_decision_views.xml',
        # menus
        'views/menus.xml'
    ],
    'assets': {
        'web.assets_qweb': [
        ],
        'web.assets_backend': [
            "ngsc_project_expense/static/src/js/*.js",
            "ngsc_project_expense/static/src/css/*.css",
        ],
    },
    'demo': [
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
