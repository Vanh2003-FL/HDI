{
    'name': 'NGSD Migrate',
    'summary': '(☞ﾟヮﾟ)☞ Entrust Consulting (❁´◡`❁)',
    'author': '(☞ﾟヮﾟ)☞ Entrust Consulting (❁´◡`❁)',
    'website': "http://entrustlab.com",
    'license': 'LGPL-3',
    'depends': [
        'ngsd_base',
        'account_reports',
        'ngsd_crm',
        'ngsd_menu',
    ],
    'data': [
        'views/wbs.xml',
        'views/ot.xml',
        'security/ir.model.access.csv',
    ],
    'auto_install': False,
    'application': True,
    'installable': True,
}
