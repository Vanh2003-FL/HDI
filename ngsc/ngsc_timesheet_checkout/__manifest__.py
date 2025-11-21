{
    "name": "Timesheet before Checkout Wizard",
    'version': '18.0.1.0.0',
    "summary": "Wizard hỗ trợ chấm công + timesheet khi checkout",
    "author": "Ngọc Tuấn",
    'license': 'LGPL-3',
    "depends": ["ngs_attendance", "ngsc_project"],
    "data": [
        "security/ir.model.access.csv",
        "views/timesheet_checkout_wizard_form.xml",
        "views/timesheet_checkout_line.xml",
        "views/timesheet_warning_wizard_form.xml",
        "views/timesheet_setting_wizard_view.xml",
        "views/menu_timesheet_config.xml"
    ],
    "assets": {
        "web.assets_backend": [
            "ngsc_timesheet_checkout/static/src/js/timesheet_check.js",
            "ngsc_timesheet_checkout/static/src/css/timesheet_checkout.css",
        ],
    },
    "installable": True,
    "application": False
}
