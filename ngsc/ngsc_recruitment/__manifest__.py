# -*- coding: utf-8 -*-
{
    'name': "Quản lý tuyển dụng",
    'summary': """Quản lý tuyển dụng""",
    'description': """ Quản lý tuyển dụng""",
    'author': "NGSC-DEVELOPER-TEAMS",
    'website': "http://ngsc.com.vn",
    'category': 'recruitment',
    'version': '0.1',
    'depends': ['website', 'hr_recruitment', 'ngsd_base','calendar', 'ngs_e_office'],
    'data': [
        # data
        'data/hr_applicant_data.xml',
        'data/mail_template.xml',
        # security
        'security/security.xml',
        'security/ir.model.access.csv',
        # wizard
        # views
        'views/skill_tag_view.xml',
        'views/source_personnel.xml',
        'views/hr_applicant_view.xml',
        'views/hr_department_views.xml',
        'views/news_job_views.xml',
        'views/news_job_templates.xml',
        'views/hr_recruitment_stage_views.xml',
        'views/recruitment_request_views.xml',
        'views/recruitment_plan_views.xml',
        'views/template_email_config.xml',
        'views/recruitment_stage.xml',
        'views/email_compose_view.xml',
        # menus
        'views/menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ngsc_recruitment/static/src/js/**.js',
            'ngsc_recruitment/static/src/scss/**.scss',
            'ngsc_recruitment/static/src/scss/**.css',
        ],
        'web.assets_qweb': [
            'ngsc_recruitment/static/src/xml/**/*',
        ],
    },
    'demo': [
    ],
    'application': True,
}