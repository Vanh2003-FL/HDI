import logging, re, os, copy, io, base64, docxtpl, locale
from datetime import datetime
from odoo import *
from pytz import timezone

_logger = logging.getLogger(__name__)

try:
    import docxtpl
except ImportError:
    _logger.debug("Can not import docxtpl`.")


class ReportDocxAbstract(models.AbstractModel):
    _inherit = 'report.report_docx.abstract'

    def create_docx_report(self, docids, data, docx_template=False):
        if docx_template:
            # try:
            objs = self._get_objs_for_report(docids, data)
            file_data = io.BytesIO()
            document = self.generate_docx_report_from_template(data, objs, docx_template)
            document.save(file_data)
            file_data.seek(0)
            return file_data.read(), "docx"
            # except Exception as e:
            #     _logger.error('A error encountered : %s ' % e)
            #     pass
        return super().create_docx_report(docids, data)

    def generate_docx_report_from_template(self, data, objs, template):
        locale.setlocale(locale.LC_TIME, self.env.context.get('lang', 'vi_VN') + '.utf8')
        inputx = io.BytesIO()
        inputx.write(base64.decodebytes(template))
        payloads = {'len': len, 'sum': sum, 'company': self.env.company, 'user': self.env.user, 'objects': objs, 'object': objs[0], 'datetime': datetime}
        document = docxtpl.DocxTemplate(inputx)
        document.render(payloads)
        return document
