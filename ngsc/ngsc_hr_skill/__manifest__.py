# -*- coding: utf-8 -*-

{
    'name': "ngsc_hr_skill",

    'summary': """
        Đánh giá và bổ sung skill nhân sự""",

    'description': """
        Đánh giá và bổ sung skill nhân sự
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
    'depends': ['ngsc_competency', 'ngsd_base'],

    # always loaded
    'data': [
        'security/hr_skill_security.xml',
        'security/ir.model.access.csv',
        'wizard/hr_employee_add_skills_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_employee_skill_views.xml',
        'views/ngsc_competency_skill_level_views.xml',
        'views/views.xml',
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'assets': {
        'web.assets_qweb': [
            "ngsc_hr_skill/static/src/xml/**/*",
        ],
        'web.assets_backend': [
            "ngsc_hr_skill/static/src/js/*.js",
            "ngsc_hr_skill/static/src/css/*.css",
        ],
    },
    'demo': [
        'demo/demo.xml',
    ],
    'installable': True,
}