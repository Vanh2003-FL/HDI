{
    'name': "Base report docx",
    'summary': "Base module to create docx report",
    'author':'Entrustlab',
    'category': 'Reporting',
    'version': '18.0.1.0.0',
    'license': 'AGPL-3',
    'depends': [
        'base', 'web',
    ],
    'data': [
    ],
    'assets': {
        'web.assets_backend': [
            'ngsd_report_docx/static/src/js/*.js'
        ],
    },
    'installable': True,
}
