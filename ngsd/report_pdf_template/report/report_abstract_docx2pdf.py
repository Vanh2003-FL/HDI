import logging, tempfile, os, subprocess, base64, jinja2, io, locale
from odoo import models
from docxtpl import InlineImage
from datetime import datetime

_logger = logging.getLogger(__name__)

from docx.shared import Mm
from docx import Document

try:
    import docxtpl
except ImportError:
    _logger.debug("Can not import docxtpl.")


class ReportDocxToPDFAbstract(models.AbstractModel):
    _name = "report.report_docx2pdf.abstract"
    _description = "Abstract Docx to PDF Report"

    def _get_objs_for_report(self, docids, data):
        if docids:
            ids = docids
        elif data and 'context' in data:
            ids = data["context"].get('active_ids', [])
        else:
            ids = self.env.context.get('active_ids', [])
        return self.env[self.env.context.get('active_model')].browse(ids)

    def create_pdf_report(self, docids, data, pdf_template=False):
        temporary_files = []
        in_file_fd, in_file_path = tempfile.mkstemp(suffix='.docx', prefix='report.fdocx2pdf.tmp.')
        os.close(in_file_fd)
        temporary_files.append(in_file_path)
        objs = self._get_objs_for_report(docids, data)
        document = self.generate_pdf_report_from_template(data, objs, pdf_template)
        document.save(in_file_path)
        out_file_dir = tempfile.gettempdir()
        out_file_path = in_file_path.replace('.docx', '.pdf')
        temporary_files.append(out_file_path)
        try:
            cmd = [
                'soffice',
                # '--headless',
                '--convert-to',
                'pdf',
                '--outdir',
                out_file_dir,
                in_file_path
            ]
            process = subprocess.call(cmd)
        except:
            raise
        with open(out_file_path, 'rb') as pdf_document:
            pdf_content = pdf_document.read()
        # Manual cleanup of the temporary files
        for temporary_file in temporary_files:
            try:
                os.unlink(temporary_file)
            except (OSError, IOError):
                _logger.error('Error when trying to remove file %s' % temporary_file)
        return pdf_content, "pdf"

    def generate_pdf_report_from_template(self, data, objs, template):
        locale.setlocale(locale.LC_TIME, self.env.context.get('lang', 'vi_VN') + '.utf8')
        inputx = io.BytesIO()
        inputx.write(base64.decodebytes(template))
        payloads = {'len': len, 'sum': sum, 'company': self.env.company, 'user': self.env.user, 'objects': objs, 'object': objs[0], 'datetime': datetime}
        document = docxtpl.DocxTemplate(inputx)
        document.render(payloads)
        return document

    def generate_pdf_report(self, data, objs):
        raise NotImplementedError()
