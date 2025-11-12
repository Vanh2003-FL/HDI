from io import BytesIO
from odoo import models
import tempfile
import os
import subprocess

import logging
_logger = logging.getLogger(__name__)

try:
    import docx
except ImportError:
    _logger.debug('Can not import python-docx.')


class ReportDocxAbstract(models.AbstractModel):
    _name = 'report.report_docx.abstract'
    _description = 'Abstract Docx Report'

    def _get_objs_for_report(self, docids, data):
        """
        Returns objects for xlx report.  From WebUI these
        are either as docids taken from context.active_ids or
        in the case of wizard are in data.  Manual calls may rely
        on regular context, setting docids, or setting data.

        :param docids: list of integers, typically provided by
            qwebactionmanager for regular Models.
        :param data: dictionary of data, if present typically provided
            by qwebactionmanager for TransientModels.
        :param ids: list of integers, provided by overrides.
        :return: recordset of active model for ids.
        """
        if docids:
            ids = docids
        elif data and 'context' in data:
            ids = data["context"].get('active_ids', [])
        else:
            ids = self.env.context.get('active_ids', [])
        return self.env[self.env.context.get('active_model')].browse(ids)

    def create_docx_report(self, docids, data):
        objs = self._get_objs_for_report(docids, data)
        file_data = BytesIO()
        document = self.generate_docx_report(data, objs)
        document.save(file_data)
        file_data.seek(0)
        return file_data.read(), 'docx'

    def generate_docx_report(self, data, objs):
        raise NotImplementedError()


    def create_docx_to_pdf_report(self, docids, data):
        temporary_files = []
        in_file_fd, in_file_path = tempfile.mkstemp(suffix='.docx', prefix='report.fdocx2pdf.tmp.')
        os.close(in_file_fd)
        temporary_files.append(in_file_path)
        objs = self._get_objs_for_report(docids, data)
        document = self.generate_docx_report(data, objs)
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
