import logging, re, os, copy, xlrd, xlsxwriter, io, base64, locale
from datetime import datetime
from odoo import models, fields, api
from pytz import timezone
from openpyxl import load_workbook

_logger = logging.getLogger(__name__)

try:
    import xlsxtpl
except ImportError:
    _logger.debug("Can not import xlsxtpl`.")

from xlsxtpl.writerx import BookWriter


class ReportXlsxAbstract(models.AbstractModel):
    _inherit = 'report.report_xlsx.abstract'

    def create_xlsx_report(self, docids, data, xlsx_template=False):
        if xlsx_template:
            try:
                objs = self._get_objs_for_report(docids, data)
                file_data = io.BytesIO()
                workbook = xlsxwriter.Workbook(file_data, self.get_workbook_options())
                xlsx = self.generate_xlsx_report_from_template(workbook, data, objs, xlsx_template)
                xlsx.save(file_data)
                file_data.seek(0)
                return file_data.read(), "xlsx"
            except Exception as e:
                _logger.error('A error encountered : %s ' % e)
                pass
        return super().create_xlsx_report(docids, data)

    def generate_xlsx_report_from_template(self, workbook, data, objs, template):
        locale.setlocale(locale.LC_TIME, self.env.context.get('lang', 'vi_VN') + '.utf8')
        inputx = io.BytesIO()
        inputx.write(base64.decodebytes(template))
        payloads = [{'len': len, 'sum': sum, 'company': self.env.company, 'user': self.env.user, 'objects': objs, 'object': objs[0], 'tpl_idx': 0, 'sheet_name': objs[0].display_name, 'datetime': datetime}]
        try:
            book = xlrd.open_workbook(file_contents=inputx.getvalue())
            payloads = [{'len': len, 'sum': sum, 'company': self.env.company, 'user': self.env.user, 'objects': objs, 'object': objs[0], 'tpl_idx': i, 'sheet_name': book.sheets()[i].name, 'datetime': datetime} for i in range(len(book.sheets()))]
        except xlrd.biffh.XLRDError:
            raise exceptions.UserError('Only excel files are supported.')
        workbook = BookWriter(inputx)
        workbook.render_book(payloads=payloads)
        return workbook
