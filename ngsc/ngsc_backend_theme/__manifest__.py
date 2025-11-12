# -*- coding: utf-8 -*-
{
    'name': 'Backend Theme',
    'version': '1.0',
    'category': 'web',
    'sequence': 100,
    'summary': 'v',
    'description': "",
    'author': "NGSC-DEVELOPER-TEAMS",
    'website': "http://ngsc.com.vn",
    'depends': ['base'],
    'data': [
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
            'ngsc_backend_theme/static/src/xml/**/*',
        ],
        'web.assets_backend': [
            "ngsc_backend_theme/static/src/js/*.js",
            "ngsc_backend_theme/static/src/css/*.css",
        ],
    },
    'license': 'LGPL-3',
}
