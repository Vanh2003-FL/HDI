# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Accounting Reports',
    'summary': 'View and create reports',
    'category': 'Accounting/Accounting',
    'description': """
Accounting Reports
    """,
    'depends': ['base', 'ngsd_entrust_dev_helper', 'ngsd_crm', 'rowno_in_tree'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/emp_department_borrow_wizard.xml',
        'data/ir_cron_data.xml',
        'views/report_financial.xml',
        'views/search_template_view.xml',
        'views/crm_account_report.xml',
        'views/crm_account_report1.xml',
        'views/kpi_account_report.xml',
        'views/contract_account_report.xml',
        'views/resource_account_report.xml',
        'views/project_account_report.xml',
        'views/wbs_account_report.xml',
        'views/version_account_report.xml',
        'views/project_resource_account_report.xml',
        'views/department_resource_account_report.xml',
        'views/timesheet_detail_by_project.xml',
        'views/timesheet_detail_by_emp.xml',
        'views/busy_rate_report.xml',
        'views/project_status_report.xml',
        'views/report_action.xml',
        'wizard/report_info_popup.xml',
        'views/department_project_report.xml',
        'views/resource_analysis_report.xml',
        'views/boundary_report.xml',
        'views/effective_resource_project_report.xml',
        'views/department_resource_detail_report.xml',
        'views/employee_department_borrow.xml',

    ],
    'auto_install': True,
    'installable': True,
    'license': 'OEEL-1',
    'assets': {
        'account_reports.assets_financial_report': [
            ('include', 'web._assets_helpers'),
            'web/static/lib/bootstrap/scss/_variables.scss',
            ('include', 'web._assets_bootstrap'),
            'web/static/fonts/fonts.scss',
            'account_reports/static/src/scss/account_financial_report.scss',
            'account_reports/static/src/scss/account_report_print.scss',
        ],
        'web.assets_backend': [
            'account_reports/static/src/js/list_controller.js',
            'account_reports/static/src/js/list_renderer.js',
            'account_reports/static/src/js/mail_activity.js',
            'account_reports/static/src/js/account_reports.js',
            'account_reports/static/src/js/action_manager_account_report_dl.js',
            'account_reports/static/src/scss/account_financial_report.scss',
        ],
        'web.assets_qweb': [
            'account_reports/static/src/xml/**/*',
        ],
    }
}