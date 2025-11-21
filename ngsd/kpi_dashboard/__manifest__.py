# Copyright 2020 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Kpi Dashboard",
    "summary": """
        Create Dashboards using kpis""",
    'version': '18.0.1.0.0',
    "license": "AGPL-3",
    "author": "Creu Blanca,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/reporting-engine",
    "depends": ["bus", "board", "base_sparse_field", 'ngsd_menu'],
    "qweb": ["static/src/xml/dashboard.xml"],
    "data": [
        "demo/demo_dashboard.xml",
        "demo/demo_dashboard_gm.xml",
        "wizards/kpi_dashboard_menu.xml",
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/kpi_kpi.xml",
        "views/kpi_dashboard.xml",
        "views/kpi_menu.xml",
    ],
    'assets': {
        'web.assets_backend': [
            'kpi_dashboard/static/src/scss/*.scss',
            'kpi_dashboard/static/src/js/*',
            'kpi_dashboard/static/src/js/widget/*',
        ],
        'web.assets_qweb': [
            'kpi_dashboard/static/src/xml/*.xml',
        ],
    },
    'installable': True,
}