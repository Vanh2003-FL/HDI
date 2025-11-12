# -*- coding: utf-8 -*-

{
    'name': "ngsc_utils",

    'summary': """
        Định nghĩa các tiện ích dùng chung cho toàn bộ hệ thống""",

    'description': """
        Định nghĩa các tiện ích dùng chung cho toàn bộ hệ thống
    """,

    'author': "NGSC-DEVELOPER-TEAMS",
    'website': "http://ngsc.com.vn",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Base',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ngsc_utils/static/src/js/**/*',
            'ngsc_utils/static/src/css/**/*',
        ],
    },
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'i18n': ['i18n/*.po'],  # Include translation file
}
