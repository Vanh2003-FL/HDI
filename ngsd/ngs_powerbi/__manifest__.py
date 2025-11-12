{
    'name': "NGS PowerBI",
    'author': 'Entrust Consulting Co., LTD - Report',
    'summary': '(TT)☞ Entrust Consulting (TT)',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'data/ir_cron.xml',
        'views/dashboard_powerbi.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ngs_powerbi/static/src/js/dashboard.js',
        ],
        'web.assets_qweb': [
            'ngs_powerbi/static/src/xml/powerbi_dashboard_tmpl.xml',
        ],
    },

    'auto_install': False,
    'application': True,
    'installable': True,
}
