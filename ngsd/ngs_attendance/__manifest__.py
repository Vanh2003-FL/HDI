{
    'name': "NGS Attendance",
    'author': 'Entrust Consulting Co., LTD - Report',
    'summary': '(TT)☞ Entrust Consulting (TT)',
    'depends': ['base', 'hr_attendance', 'ngsd_base', 'ngs_e_office', 'hr_attendance_geolocation'],
    'data': [
        'security/groups.xml',
        'security/ir_rule.xml',
        'views/hr_work_location.xml',
        'views/res_config_settings.xml',
        'views/hr_attendance_explanation.xml',
        'views/hr_attendance.xml',
        'views/resource_calendar.xml',
        'views/timesheet_view.xml',
        'security/ir.model.access.csv',
        'report/report_action.xml',
        'wizard/reason_for_refuse_wizard.xml',
        'wizard/report_timekeeping.xml',
        'wizard/explanation_task_timesheet.xml',
        'data/message_subtypes.xml',
        'data/ir_cron.xml',
        'views/menu.xml',
    ],
    'assets': {
        'web.assets_qweb': [
            'ngs_attendance/static/src/xml/*.xml',
        ],
        'web.assets_backend': [
            'ngs_attendance/static/src/js/*.js',
        ],
    },

    'auto_install': False,
    'application': True,
    'installable': True,
}
