{
    'name': 'NGSC - Nâng cấp chấm công bất đồng bộ',
    'version': '18.0.1.0.0',
    'summary': 'Ghi nhận chấm công bất đồng bộ, chống bấm nút 2 lần, quy trình phê duyệt và bảo trì dữ liệu',
    'author': 'Odoo Team',
    'website': 'https://erp-ngsc.com.vn/',
    'depends': ['base', 'hr', 'hr_attendance', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_attendance_log.xml',
        'views/hr_attendance_log_views.xml',
    ],
    "assets": {
        "web.assets_backend": [
            "ngs_hr_attendance_async/static/src/js/hr_attendances_block_click.js",
        ],
    },
    'qweb': [],
    'installable': True,
    'application': False,
}
