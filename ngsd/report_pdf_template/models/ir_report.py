from odoo import api, fields, models, exceptions
import docx, io, base64


class ReportAction(models.Model):
    _inherit = "ir.actions.report"

    pdf_template = fields.Binary(string='Pdf Template')
    pdf_template_name = fields.Char(string='Pdf Template File Name')

    @api.model
    def _render_docx2pdf(self, report_ref, docids, data):
        report_model_name = "report.%s" % self.report_name
        report_model = self.env.get(report_model_name)
        if report_model is None:
            report_model = self.env.get("report.report_docx2pdf.abstract")
        return (
            report_model.with_context(active_model=self.model)
                .sudo(False)
                .create_pdf_report(docids, data, self.pdf_template)
        )

    @api.model
    def _get_report_from_name(self, report_name):
        res = super(ReportAction, self)._get_report_from_name(report_name)
        if res:
            return res
        report_obj = self.env["ir.actions.report"]
        qwebtypes = ["qweb-pdf"]
        conditions = [
            ("report_type", "in", qwebtypes),
            ("report_name", "=", report_name),
        ]
        context = self.env["res.users"].context_get()
        return report_obj.with_context(**context).search(conditions, limit=1)

    @api.constrains('pdf_template', 'report_type')
    def _constrains_pdf_template_extension(self):
        for rec in self:
            if not rec.pdf_template or rec.report_type != 'qweb-pdf': continue
            try:
                inputx = io.BytesIO()
                inputx.write(base64.decodebytes(rec.pdf_template))
                book = docx.Document(inputx)
            except ValueError as e:
                raise exceptions.UserError('Only docx files are supported.')
