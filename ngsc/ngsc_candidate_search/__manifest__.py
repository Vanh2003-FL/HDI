# -*- coding: utf-8 -*-
{
    'name': "ngsc_candidate_search",
    'summary': """
        Tìm kiếm nguồn lực nhân sự""",
    'description': """
        Tìm kiếm nguồn lực nhân sự
    """,
    'author': "NGSC-DEVELOPER-TEAMS",
    'website': "http://ngsc.com.vn",
    'category': 'Human Resources',
    'version': '0.1',
    'depends': ['ngsc_hr_skill', 'account_reports'],
    'data': [
        # data

        # security
        'security/security.xml',
        'security/ir.model.access.csv',
        # wizard

        # views
        'views/compare_candidates.xml',
        'views/ngsc_candidate_search_views.xml',
        'views/ngsc_candidate_search_result_views.xml',
        # menus
        'views/menu.xml',
    ],
    'assets': {
        'web.assets_qweb': [
            "ngsc_candidate_search/static/src/xml/**/*",
        ],
        'web.assets_backend': [
            "ngsc_candidate_search/static/src/js/*.js",
            "ngsc_candidate_search/static/src/css/*.css",
            "ngsc_candidate_search/static/src/css/compare_candidate.scss"
        ],
    },
    'demo': [
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
