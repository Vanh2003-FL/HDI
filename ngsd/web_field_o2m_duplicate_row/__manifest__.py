{
    'name': 'One2many Duplicate Row',
    'summary': 'Add Copy Button to Duplicate a Row on One2many field',
    'category': 'hidden',
    'author': 'Hoang Minh Hieu',
    'license': 'LGPL-3',
    'depends': [
        'web',
    ],
    'assets': {
        'web.assets_backend': [
            'web_field_o2m_duplicate_row/static/src/scss/*.scss',
            'web_field_o2m_duplicate_row/static/src/js/*',
        ],
    },
    'installable': True,
}