{
    'name': "NGS - Reporting Engine",
    'author': 'Entrust Consulting Co., LTD - ERP',
    'license': 'LGPL-3',
    'depends': ['web', 'base', 'report_docx_template', 'report_xlsx_template', 'report_pdf_template', 'ngsd_entrust_dev_helper'],
    'data': [
        'security/ir.model.access.csv',
        'views/report_template.xml'
    ],
    'assets': {},
    'installable': True,
    'application': True,
}
