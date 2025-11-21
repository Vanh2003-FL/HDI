# -*- coding: utf-8 -*-

{
    'name': "ngsc_competency",

    'summary': """
        Module khung năng lực và các skill""",

    'description': """
        Module khung năng lực và các skill
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
    'depends': ['base', 'ngsc_constance', 'ngsc_utils', 'mail', 'web'],
    # always loaded
    'data': [
        'security/competency_security.xml',
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
        'views/skill_view.xml',
        'views/range_point_view.xml',
        'views/skill_group_view.xml',
        'views/competency_tag_view.xml',
        'data/range_point.xml',
        'data/skill_group.xml',
        # allway in bottom
        'views/menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ngsc_competency/static/js/**/*',
            'ngsc_competency/static/css/**/*',
        ],
    },
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'application': True,
    'installable': True,
}