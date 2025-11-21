{
    'name': "NGS Hr",
    'author': 'NGSC',
    'license': 'LGPL-3',
    'summary': 'NGSC',
    'depends': ['base', 'hr_skills', 'ngsd_base', 'hr_holidays'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence.xml',
        'views/res_users.xml',
        'views/hr_employee_views.xml'
    ],
    'assets': {
    },
    'auto_install': False,
    'application': True,
    'installable': True,
}
