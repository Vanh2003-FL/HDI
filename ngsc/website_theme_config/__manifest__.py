{
    'name': 'Cấu hình theme NGSC',
    'version': '18.0.1.0.0',
    'summary': 'Tùy chỉnh giao diện backend Odoo (background, header, footer, button)',
    'category': 'Tools',
    'author': 'Odoo Team',
    'website': 'https://erp-ngsc.com.vn/',
    'license': 'LGPL-3',
    'depends': ['ngsd_base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/theme_option_views.xml',
        'views/theme_assets.xml',
        'views/website_theme_menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'website_theme_config/static/src/css/theme.css',
            'website_theme_config/static/src/css/color_palette.css',
            'website_theme_config/static/src/js/color_palette.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
