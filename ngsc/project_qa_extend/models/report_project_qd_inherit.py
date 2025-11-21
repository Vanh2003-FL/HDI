# -*- coding: utf-8 -*-
from odoo import models, _


class ReportQDTLDAOverride(models.AbstractModel):
    _inherit = 'report.ngsd_report.report_qdtlda'

    def generate_docx_report(self, data, objs):
        # Gọi hàm gốc để lấy document đã render sẵn
        document = super().generate_docx_report(data, objs)

        # Nếu có field QA mới thì render lại đúng giá trị
        if objs and hasattr(objs, 'en_project_qa_ids'):
            ctx = {
                'en_project_qa_ids': ', '.join(objs.en_project_qa_ids.mapped('display_name'))
            }
            document.render(ctx)

        return document


class ReportQDDCDAOverride(models.AbstractModel):
    _inherit = 'report.ngsd_report.report_qddcda'

    def generate_docx_report(self, data, objs):
        # Gọi hàm gốc để lấy document đã render sẵn
        document = super().generate_docx_report(data, objs)

        # Nếu có field QA mới thì render lại đúng giá trị
        if objs and hasattr(objs, 'en_project_qa_ids'):
            ctx = {
                'en_project_qa_ids': ', '.join(objs.en_project_qa_ids.mapped('display_name'))
            }
            document.render(ctx)

        return document
