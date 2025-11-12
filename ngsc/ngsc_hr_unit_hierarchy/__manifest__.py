# -*- coding: utf-8 -*-
{
    'name': 'Phân cấp phòng ban',
    'version': '1.0',
    'category': 'HR',
    'sequence': 1000,
    'summary': 'Phân cấp phòng ban',
    'description': "",
    'author': "NGSC-DEVELOPER-TEAMS",
    'website': "http://ngsc.com.vn",
    'depends': ['ngsd_base'],
    'data': [
        'security/ir.model.access.csv',

        'views/hr_employee_views.xml',
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
        ],
        'web.assets_backend': [
        ],
        "web.assets_backend_legacy_lazy": [
        ],
        'web.assets_tests': [
        ],
        'web.qunit_suite_tests': [
        ],
    },
    'license': 'LGPL-3',
}
