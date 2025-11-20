from odoo import fields, models, api, exceptions
from datetime import timedelta
from odoo.exceptions import ValidationError, UserError
import pathlib

try:
    from docxtpl import DocxTemplate
    DOCXTPL_AVAILABLE = True
except ImportError:
    DocxTemplate = None
    DOCXTPL_AVAILABLE = False


class ReportQDTLDA(models.AbstractModel):
    _name = 'report.ngsd_report.report_qdtlda'
    _inherit = 'report.report_docx.abstract'

    def generate_docx_report(self, data, objs):
        if not DOCXTPL_AVAILABLE:
            raise ValidationError('Gói docxtpl chưa được cài đặt. Vui lòng cài đặt: pip install python-docx docxtpl')
        if not objs:
            raise ValidationError('Không tìm thấy bản ghi Dự án!')
        template_name = 'qdtlda.docx'
        if not template_name:
            raise ValidationError('Không tìm thấy mẫu xuất docx!')
        template_file = pathlib.Path(__file__).parent.parent.joinpath('static', 'docx', template_name)
        try:
            document = DocxTemplate(template_file)
        except FileNotFoundError:
            raise ValidationError("Error: Could not find template {}").format(template_name)
        lines = [{
            'stt': idx,
            'name': line.employee_id.display_name or '',
            'role': line.role_id.display_name or '',
        } for idx, line in enumerate(objs.en_resource_ids.filtered(lambda r: r.state == 'approved').order_line, start=1)]
        ctx = {
            'name': objs.name or '',
            'partner_name': objs.partner_id.display_name or '',
            'date': f"{objs.date_start.strftime('%d/%m/%Y') if objs.date_start else ''} - {objs.date.strftime('%d/%m/%Y') if objs.date else ''}",
            'en_code': objs.en_code or '',
            'en_project_manager_id': objs.en_project_manager_id.display_name or '',
            'user_id': objs.user_id.display_name or '',
            'en_project_sale_id': objs.en_project_sale_id.display_name or '',
            'en_project_qa_id': objs.en_project_qa_id.display_name or '',
            'en_project_implementation_id': objs.en_project_implementation_id.display_name or '',
            'en_project_accountant_id': objs.en_project_accountant_id.display_name or '',
            'lines': lines
        }
        document.render(ctx)
        return document


class ReportQDDCDA(models.AbstractModel):
    _name = 'report.ngsd_report.report_qddcda'
    _inherit = 'report.report_docx.abstract'

    def generate_docx_report(self, data, objs):
        if not objs:
            raise ValidationError('Không tìm thấy bản ghi Dự án!')
        template_name = 'qddcda.docx'
        if not template_name:
            raise ValidationError('Không tìm thấy mẫu xuất docx!')
        template_file = pathlib.Path(__file__).parent.parent.joinpath('static', 'docx', template_name)
        try:
            document = DocxTemplate(template_file)
        except FileNotFoundError:
            raise ValidationError("Error: Could not find template {}").format(template_name)
        lines = [{
            'stt': idx,
            'name': line.employee_id.display_name or '',
            'role': line.role_id.display_name or '',
        } for idx, line in enumerate(objs.en_resource_ids.filtered(lambda r: r.state == 'approved').order_line, start=1)]
        ctx = {
            'name': objs.name or '',
            'partner_name': objs.partner_id.display_name or '',
            'date': f"{objs.date_start.strftime('%d/%m/%Y') if objs.date_start else ''} - {objs.date.strftime('%d/%m/%Y') if objs.date else ''}",
            'en_code': objs.en_code or '',
            'en_project_manager_id': objs.en_project_manager_id.display_name or '',
            'user_id': objs.user_id.display_name or '',
            'en_project_sale_id': objs.en_project_sale_id.display_name or '',
            'en_project_qa_id': objs.en_project_qa_id.display_name or '',
            'en_project_implementation_id': objs.en_project_implementation_id.display_name or '',
            'en_project_accountant_id': objs.en_project_accountant_id.display_name or '',
            'lines': lines
        }
        document.render(ctx)
        return document

