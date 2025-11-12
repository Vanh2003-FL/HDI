{
    'name': 'NGS - E Office',
    'summary': '(☞ﾟヮﾟ)☞ Entrust Consulting (❁´◡`❁)',
    'author': '(☞ﾟヮﾟ)☞ Entrust Consulting (❁´◡`❁)',
    'website': "http://entrustlab.com",
    'depends': [
        'base',
        'calendar',
        'approvals',
        'ngsd_base',
        'account_asset',
    ],
    'data': [
        'data/request_support.xml',
        'security/res_groups.xml',
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'views/product_product.xml',
        'views/approval_product_line_views.xml',
        'views/approval_category.xml',
        'views/approval_request.xml',
        'views/room_booking_views.xml',
        'views/room_room_views.xml',
        'views/room_office_views.xml',
        'views/account_asset_views.xml',
        'views/approve.xml',
        'views/res_supplier_view.xml',
        'views/menu.xml',
        'views/business_plan.xml'
    ],
    'license': 'LGPL-3',
    "assets": {
        "web.assets_qweb": [
            "ngs_e_office/static/src/xml/**/*",
        ],
        "web.assets_backend": [
            "ngs_e_office/static/src/js/*.js",
            "ngs_e_office/static/src/scss/*.scss",
        ],
    },
    'auto_install': False,
    'application': True,
    'installable': True,
}
