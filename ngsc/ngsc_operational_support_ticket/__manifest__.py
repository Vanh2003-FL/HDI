# -*- coding: utf-8 -*-
{
    'name': "ngsc_operational_support_ticket",
    'summary': """
        Hỗ trợ vận hành""",
    'description': """
        Hỗ trợ vận hành
    """,
    'author': "NGSC-DEVELOPER-TEAMS",
    'website': "http://ngsc.com.vn",
    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Project',
    'version': '0.1',
    # any module necessary for this one to work correctly
    'depends': ['helpdesk'],
    # always loaded
    'data': [
        # data
        # security
        'security/ir.model.access.csv',
        # wizard
        # views
        "views/operational_support_ticket.xml",
        "views/helpdesk_ticket_views.xml",
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
