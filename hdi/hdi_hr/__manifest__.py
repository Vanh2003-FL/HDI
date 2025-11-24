# -*- coding: utf-8 -*-
{
  'name': 'HDI HR Management',
  'version': '18.0.1.0.0',
  'category': 'hdi',
  'summary': 'HDI HRM',
  'description': """
        HDI Human Resources Management Extensions
    """,
  'author': 'HDI Development Team',
  'website': 'https://hditech.com.vn',
  'license': 'LGPL-3',

  'depends': [
    # Odoo 18 Core
    'base',
    'mail',
    'web',

    # Odoo 18 HR Standard Modules (chỉ những module có sẵn)
    'hr',  # Core HR - Employee Management
    'hr_holidays',  # Leave Management (renamed in Odoo 18)
    'hr_attendance',  # Attendance Tracking
    'hr_contract',  # Contract Management

    # Additional integrations
    'calendar',  # For meeting integration
    'resource',  # For working time/calendar
  ],

  'data': [
    # Security
    'security/hdi_hr_security.xml',
    'security/ir.model.access.csv',

    # Data
    'data/ir_sequence.xml',
    'data/hdi_hr_settings.xml',

    # Views - Employee
    'views/hr_employee_views.xml',
    'views/hr_department_views.xml',
    'views/hr_job_views.xml',
    'views/hr_leave_views.xml',

    # Views - Skills & Competency
    'views/hr_skill_views.xml',
    'views/hr_employee_skill_views.xml',
    'views/hdi_skills_competency_views.xml',
    'views/hdi_skill_assessment_views.xml',
    'views/hdi_performance_evaluation_views.xml',

    # Views - Performance
    'views/hr_evaluation_views.xml',

    # Views - Contract & Payroll
    # Root menu (loaded early so other files can reference the root)
    'views/hdi_hr_menu_root.xml',

    'views/hdi_contract_payroll_views.xml',
    'views/hdi_payroll_component_views.xml',

    # Views - Leave Advanced (loaded before menu so actions are available)
    'views/hdi_leave_advanced_views.xml',

    # Full menus (menu items that reference actions are loaded after actions)
    'views/hdi_hr_menu.xml',

    # Views - Configuration
    'views/res_config_settings_views.xml',

    # Wizards
    'wizard/hr_employee_onboarding_wizard_views.xml',

    # Reports
    'report/hr_employee_report_templates.xml',

  ],

  'demo': [],

  'assets': {
    'web.assets_backend': [
      'hdi_hr/static/src/css/hdi_hr.css',
      'hdi_hr/static/src/js/hdi_hr_dashboard.js',
    ],
  },

  'images': ['static/description/icon.png'],

  'installable': True,
  'application': True,
  'auto_install': False,
}
