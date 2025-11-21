{
    'name': 'Mapping dữ liệu giữa Employee và Partner',
    'version': '18.0.1.0.0',
    'summary': 'Liên kết Employee ↔ Partner để chọn đầy đủ người tham dự',
    'description': 'Cho phép chọn đầy đủ nhân viên trong danh sách người tham dự.',
    'author': 'Odoo team',
    'license': 'LGPL-3',
    'depends': ['hr', 'calendar'],
    'data': [
        'security/ir.model.access.csv',
        'data/cron_sync_employee_partner.xml',
        'views/calendar_event_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
