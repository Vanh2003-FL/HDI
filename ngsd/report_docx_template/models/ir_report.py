from odoo import models, fields, api, _, exceptions
import docx, io, base64


class ReportAction(models.Model):
    _inherit = "ir.actions.report"

    docx_template = fields.Binary(string='Docx Template')
    docx_template_name = fields.Char(string='Docx Template File Name')

    @api.model
    def render_docx(self, docids, data):
        if self.docx_template:
            report_model_name = "report.%s" % self.report_name
            report_model = self.env.get(report_model_name)
            if report_model is None:
                report_model = self.env.get("report.report_docx.abstract")
            return (
                report_model.with_context(active_model=self.model)
                    .sudo(False)
                    .create_docx_report(docids, data, self.docx_template)
            )
        return super().render_docx(docids, data)

    @api.constrains('docx_template', 'report_type')
    def _constrains_docx_template_extension(self):
        for rec in self:
            if not rec.docx_template or rec.report_type != 'docx': continue
            try:
                inputx = io.BytesIO()
                inputx.write(base64.decodebytes(rec.docx_template))
                book = docx.Document(inputx)
            except ValueError as e:
                raise exceptions.UserError('Only docx files are supported.')
