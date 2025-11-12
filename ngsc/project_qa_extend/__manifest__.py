{
    'name': 'Project QA Extend',
    'version': '1.0',
    'depends': ['project', 'hr','ngsc_project', 'ngsd_base', 'ngsc_reporting', 'ngsc_constance', 'ngsc_utils'],
    'author': 'NGSC-ODOO-TEAMS',
    'category': 'project',
    'website': "http://erp-ngsc.com.vn",
    'description': 'Thêm trường QA dự án dạng Many2many thay thế trường cũ Many2one',
    'data': [
        "security/project_qa_rule.xml",
        "security/ir_rule_qam_override.xml",
        'views/project_view_inherit.xml',
        'views/project_decision_inderit_view.xml',
        'views/project_status_report_inherit_views.xml',
    ],
    'installable': True,
    'application': False,
}
