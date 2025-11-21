from odoo import models, fields, api, _, exceptions
import xlrd, xlsxwriter
from datetime import datetime
import io
import base64
from dateutil.relativedelta import relativedelta
import time, math, pytz
from pytz import timezone, utc
from odoo.exceptions import UserError


import logging

_logger = logging.getLogger(__name__)

datemode = 0


class ImportWBSPopup(models.TransientModel):
    _name = 'import.wbs.popup'

    file = fields.Binary('File')
    file_name = fields.Char('File name')

    def import_data(self):
        project = self.env[self._context.get('active_model')].browse(self._context.get('active_id'))
        wbs = self.env['en.wbs'].create({
            'project_id': project.id,
            'resource_plan_id': project.en_resource_ids.filtered(lambda r: r.state == 'approved').id,
            'user_id': self.env.user.id
        })
        # Import giai đoạn
        self.batch_import_data(sheet="Import giai đoạn", model="en.project.stage", wbs=wbs, match_field="wbs_version.id")
        # Import Gói công việc
        self.batch_import_data(sheet="Import Gói công việc", model="en.workpackage", wbs=wbs, match_field="wbs_version.id")
        # Import Công việc
        self.batch_import_data(sheet="Import Công việc", model="project.task", wbs=wbs, match_field='en_wbs_id.id')

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': 'Đã import thành công WBS %s!'%wbs.version_number,
                'title': 'Thành công',
                'type': 'success',
                'sticky': True,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    def batch_import_data(self, sheet, model, wbs, match_field):
        stage_import = self.env['base_import.import'].create({
            'res_model': model,
            'file': base64.decodebytes(self.file),
            'file_name': self.file_name,
            'file_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        preview = stage_import.parse_preview({
            "has_headers": True,
            "advanced": True,
            "keep_matches": False,
            "name_create_enabled_fields": {},
            "import_set_empty_fields": [],
            "import_skip_records": [],
            "fallback_values": {},
            "skip": 0,
            "limit": 10000,
            "encoding": "",
            "separator": "",
            "quoting": "\"",
            "sheet": sheet,
            "date_format": "",
            "datetime_format": "",
            "float_thousand_separator": ",",
            "float_decimal_separator": ".",
            "fields": [],
            "import_order_line": match_field,
            "import_field": match_field,
            "order_id": wbs.id
        })
        matches = preview.get('matches', {})
        if not matches:
            raise UserError(f'Sheet {sheet} không thể map trường')
        fs = [matches[k][0] for k in matches]
        headers = preview.get('headers', {})
        options = preview.get('options', {})
        result = stage_import.execute_import(
            fs, headers, options
        )
        messages = result.get('messages')
        if messages:
            dat_message = ['Sheet ' + sheet]
            dat_message += [k.get('message') for k in messages]
            raise UserError('\n-----------------------------\n'.join(dat_message))
