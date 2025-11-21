from odoo import models, fields, api, _, exceptions
import xlrd, io, base64


class ReportAction(models.Model):
    _inherit = "ir.actions.report"

    xlsx_template = fields.Binary(string='Xlsx Template')
    xlsx_template_name = fields.Char(string='Xlsx Template File Name')

    @api.model
    def _render_xlsx(self, docids, data):
        if self.xlsx_template:
            report_model_name = "report.%s" % self.report_name
            report_model = self.env.get(report_model_name)
            if report_model is None:
                report_model = self.env.get("report.report_xlsx.abstract")
            return (
                report_model.with_context(active_model=report_model.model)
                    .sudo(False)
                    .create_xlsx_report(docids, data, self.xlsx_template)
            )
        return super()._render_xlsx(docids, data)

    @api.constrains('xlsx_template', 'report_type')
    def _constrains_xlsx_template_extension(self):
        for rec in self:
            if not rec.xlsx_template or rec.report_type != 'xlsx': continue
            try:
                inputx = io.BytesIO()
                inputx.write(base64.decodebytes(rec.xlsx_template))
                book = xlrd.open_workbook(file_contents=inputx.getvalue())
            except xlrd.biffh.XLRDError:
                raise exceptions.UserError('Only excel files are supported.')
