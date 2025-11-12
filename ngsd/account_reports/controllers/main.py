# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import content_disposition, request
from odoo.addons.web.controllers.main import _serialize_exception

import json
from odoo.tools import html_escape, osutil
import operator
from odoo.addons.web.controllers.main import GroupsTreeNode
from odoo.addons.web.controllers.main import ExportFormat
from odoo import fields as fields_base


def base(self, data):
    params = json.loads(data)
    model, fields, ids, domain, import_compat = \
        operator.itemgetter('model', 'fields', 'ids', 'domain', 'import_compat')(params)

    Model = request.env[model].with_context(import_compat=import_compat, **params.get('context', {}))
    if not Model._is_an_ordinary_table():
        fields = [field for field in fields if field['name'] != 'id']

    field_names = [f['name'] for f in fields]
    if import_compat:
        columns_headers = field_names
    else:
        columns_headers = [val['label'].strip() for val in fields]

    groupby = params.get('groupby')
    if not import_compat and groupby:
        groupby_type = [Model._fields[x.split(':')[0]].type for x in groupby]
        domain = [('id', 'in', ids)] if ids else domain
        groups_data = Model.read_group(domain, [x if x != '.id' else 'id' for x in field_names], groupby, lazy=False)

        # read_group(lazy=False) returns a dict only for final groups (with actual data),
        # not for intermediary groups. The full group tree must be re-constructed.
        tree = GroupsTreeNode(Model, field_names, groupby, groupby_type)
        for leaf in groups_data:
            tree.insert_leaf(leaf)

        response_data = self.from_group_data(fields, tree)
    else:
        records = Model.browse(ids) if ids else Model.search(domain, offset=0, limit=False, order=False)

        export_data = records.export_data(field_names).get('datas',[])
        response_data = self.from_data(columns_headers, export_data)

    # TODO: call `clean_filename` directly in `content_disposition`?
    if model == 'account.analytic.line':
        file_name = 'Dữ liệu Timesheet'
    else:
        file_name = self.filename(model)
    if params.get('context', {}).get('show_export_odoo_button'):
        context = params.get('context', {})
        model_name = request.env['ir.model']._get(model).name
        date_start = fields_base.Date.from_string(context.get('date_from')).strftime('%d%m%Y')
        date_to = fields_base.Date.from_string(context.get('date_to')).strftime('%d%m%Y')
        file_name = f'{model_name}_{date_start}_đến_{date_to}'
    return request.make_response(response_data,
        headers=[('Content-Disposition',
                        content_disposition(
                            osutil.clean_filename(file_name + self.extension))),
                 ('Content-Type', self.content_type)],
    )


ExportFormat.base = base


class FinancialReportController(http.Controller):

    @http.route('/account_reports', type='http', auth='user', methods=['POST'], csrf=False)
    def get_report(self, model, options, output_format, financial_id=None, **kw):
        uid = request.session.uid
        account_report_model = request.env['account.report']
        options = json.loads(options)
        cids = request.httprequest.cookies.get('cids', str(request.env.user.company_id.id))
        allowed_company_ids = [int(cid) for cid in cids.split(',')]
        report_obj = request.env[model].with_user(uid).with_context(allowed_company_ids=allowed_company_ids)
        if financial_id and financial_id != 'null':
            report_obj = report_obj.browse(int(financial_id))
        report_name = report_obj.get_report_filename(options)
        try:
            if output_format == 'xlsx':
                response = request.make_response(
                    None,
                    headers=[
                        ('Content-Type', account_report_model.get_export_mime_type('xlsx')),
                        ('Content-Disposition', content_disposition(report_name + '.xlsx'))
                    ]
                )
                response.stream.write(report_obj.get_xlsx(options))
            if output_format == 'pdf':
                response = request.make_response(
                    report_obj.get_pdf(options),
                    headers=[
                        ('Content-Type', account_report_model.get_export_mime_type('pdf')),
                        ('Content-Disposition', content_disposition(report_name + '.pdf'))
                    ]
                )
            if output_format == 'xml':
                content = report_obj.get_xml(options)
                response = request.make_response(
                    content,
                    headers=[
                        ('Content-Type', account_report_model.get_export_mime_type('xml')),
                        ('Content-Disposition', content_disposition(report_name + '.xml')),
                        ('Content-Length', len(content))
                    ]
                )
            if output_format == 'xaf':
                content = report_obj.get_xaf(options)
                response = request.make_response(
                    content,
                    headers=[
                        ('Content-Type', account_report_model.get_export_mime_type('xaf')),
                        ('Content-Disposition', content_disposition(report_name + '.xaf')),
                        ('Content-Length', len(content))
                    ]
                )
            if output_format == 'txt':
                content = report_obj.get_txt(options)
                response = request.make_response(
                    content,
                    headers=[
                        ('Content-Type', account_report_model.get_export_mime_type('txt')),
                        ('Content-Disposition', content_disposition(report_name + '.txt')),
                        ('Content-Length', len(content))
                    ]
                )
            if output_format == 'csv':
                content = report_obj.get_csv(options)
                response = request.make_response(
                    content,
                    headers=[
                        ('Content-Type', account_report_model.get_export_mime_type('csv')),
                        ('Content-Disposition', content_disposition(report_name + '.csv')),
                        ('Content-Length', len(content))
                    ]
                )
            if output_format == 'zip':
                content = report_obj._get_zip(options)
                response = request.make_response(
                    content,
                    headers=[
                        ('Content-Type', account_report_model.get_export_mime_type('zip')),
                        ('Content-Disposition', content_disposition(report_name + '.zip')),
                    ]
                )
                # Adding direct_passthrough to the response and giving it a file
                # as content means that we will stream the content of the file to the user
                # Which will prevent having the whole file in memory
                response.direct_passthrough = True
            return response
        except Exception as e:
            se = _serialize_exception(e)
            error = {
                'code': 200,
                'message': 'Odoo Server Error',
                'data': se
            }
            return request.make_response(html_escape(json.dumps(error)))
