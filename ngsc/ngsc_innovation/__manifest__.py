{
    'name': "Ý tưởng sáng tạo",
    'summary': "Quản lý ý tưởng sáng tạo trong công ty",
    'description': """
        Module quản lý ý tưởng sáng tạo:
        - Nhân viên gửi ý tưởng
        - Bộ phận Truyền thông nội bộ duyệt
        - Hội đồng đánh giá chấm điểm
    """,
    'author': "NGSC Odoo Team",
    'website': "http://www.ngsc.com.vn",
    'category': 'Human Resources',
    'license': 'LGPL-3',
    'depends': ['ngsd_base'],
    'external_dependencies': {
        'python': ['xlsxwriter'],
    },
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/mail_template.xml',
        'data/ngsc_innovation_evaluation_period_data.xml',
        'wizard/ngsc_innovation_reject_wizard_view.xml',
        'wizard/ngsc_innovation_ttnb_scoring_wizard_view.xml',
        'views/ngsc_innovation_idea_view.xml',
        'views/ngsc_innovation_summary_views.xml',
        'wizard/ngsc_innovation_scoring_wizard_view.xml',
        'views/ngsc_innovation_evaluation_board_views.xml',
        'views/ngsc_innovation_evaluation_period_views.xml',
        'views/ngsc_version_criteria_views.xml',
        'views/ngsc_innovation_config_views.xml',
        'views/pdf_upload_view.xml',
        'views/res_users_evaluation_board_views.xml',
        'views/ngsc_innovation_menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ngsc_innovation/static/src/js/ngsc_pdf_client_action.js',
        ],
    },
    'installable': True,
    'application': True,
}