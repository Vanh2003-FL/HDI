{
    "name": "Base report xlsx",
    "summary": "Base module to create xlsx report",
    "author": "ACSONE SA/NV," "Creu Blanca," "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/reporting-engine",
    "category": "Reporting",
    "version": "18.0.1.0.5",
    "development_status": "Mature",
    "license": "AGPL-3",
    "external_dependencies": {"python": ["openpyxl"]},
    "depends": ["base", "web"],
    "installable": True,
    "assets": {
        "web.assets_backend": [
            "ngsd_report_xlsx/static/src/js/report/action_manager_report.esm.js",
        ],
    },
}
