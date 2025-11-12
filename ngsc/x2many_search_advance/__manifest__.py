# -*- coding: utf-8 -*-
{
    'name': "X2Many Tree Search",

    'summary': """Search Record in one2many or many2many Record""",

    'description': """
       Search Record in one2many or many2many Record
    """,

    'license': 'LGPL-3',
    'author': "Brain Station 23",
    'website': "https://brainstation-23.com/",
    'category': 'Search',
    'version': '18.0.1.0.0',
    'depends': ['web'],
    'assets': {
        'web.assets_backend': [
            'x2many_search_advance/static/src/js/custom_list_renderer.js',
        ],
    },
    'images': [
        'static/description/banner.gif'
    ],
    'application': True,
    'installable': True,
    'support': 'support@brainstation-23.com',
}
