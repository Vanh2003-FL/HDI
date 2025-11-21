# -*- coding: utf-8 -*-
{
    'name': "Migration WBS",
    'summary': """Migration WBS""",
    'description': """Migration WBS""",
    'author': "NGSC-DEVELOPER-TEAMS",
    'website': "http://ngsc.com.vn",
    'category': 'Project',
    'version': '18.0.1.0.0',
    'depends': ['ngsc_project_wbs'],
    'data': [
        # data
        'data/ir_cron.xml',
        # security
        # wizard
        # views
        # menus
    ],
    'assets': {
        'web.assets_qweb': [
        ],
        'web.assets_backend': [
        ],
    },
    'demo': [
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
