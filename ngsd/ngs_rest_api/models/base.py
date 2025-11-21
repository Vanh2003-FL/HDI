from odoo.addons.component.core import Component
from odoo.tools.safe_eval import safe_eval
from odoo.addons.base_rest import restapi
# from odoo.addons.base_rest_datamodel.restapi import Datamodel
from odoo import models, fields, api, _
from odoo.addons.base_rest.components.service import to_bool, to_int
from pytz import timezone, UTC
from dateutil.relativedelta import relativedelta
from datetime import timedelta, datetime, date, time
from dateutil import parser
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT


class Base(models.AbstractModel):
    _inherit = "base"

    def to_values(self, values, fields_lst):
        vals = {}
        dict_values = values.dump()
        fields_get = self.fields_get()
        for key in dict_values:
            if key not in fields_lst or not fields_get.get(fields_lst[key]):
                continue
            if not dict_values[key]:
                continue
            if fields_get.get(fields_lst[key]).get('type') == 'date':
                vals[fields_lst[key]] = parser.parse(dict_values[key])
                continue
            if fields_get.get(fields_lst[key]).get('type') == 'datetime':
                vals[fields_lst[key]] = self.datetime_localize(parser.parse(dict_values[key]), self.env.user.tz, 'UTC')
                continue
            if fields_get.get(fields_lst[key]).get('type') == 'many2one':
                record = self.env[fields_get[fields_lst[key]].get('relation')].name_search(dict_values[key], limit=1)
                if not vals.get(fields_lst[key]):
                    vals[fields_lst[key]] = record[0][0] if record else False
                continue
            if fields_get.get(fields_lst[key]).get('type') in ['many2many', 'one2many']:
                record = self.env[fields_get[fields_lst[key]].get('relation')].name_search(dict_values[key], limit=1)
                vals[fields_lst[key]] = [(6, 0, [record[0][0]])] if record else False
                continue

            vals[fields_lst[key]] = dict_values[key]
        return vals

    def datetime_localize(self, datetime, from_tz, to_tz):
        return timezone(from_tz).localize(datetime).astimezone(timezone(to_tz)).replace(tzinfo=None)

    def to_result(self, record, fields_lst, model):
        res = {}
        schema = self.env.datamodels[model].get_schema()
        fields_schema = schema.fields
        fields_get = self.fields_get()
        for field in fields_lst:
            if '.' in fields_lst[field]:
                data = record.mapped(fields_lst[field])[0] if record.mapped(fields_lst[field]) and record.mapped(fields_lst[field])[0] else ''
                if isinstance(data, datetime):
                    lang = self._context.get("lang")
                    langs = self.env['res.lang']._lang_get(lang)
                    time_format = langs.time_format or DATETIME_FORMAT
                    res.update({field: str(self.datetime_localize(data, 'UTC', self.env.user.tz or 'Asia/Ho_Chi_Minh').strftime(time_format)) if data else ''})
                    continue
                if isinstance(data, date):
                    lang = self._context.get("lang")
                    langs = self.env['res.lang']._lang_get(lang)
                    date_format = langs.date_format or DATE_FORMAT
                    res.update({field: str(data.strftime(date_format)) if data else ''})
                    continue
                res.update({field: record.mapped(fields_lst[field])[0] if record.mapped(fields_lst[field]) and record.mapped(fields_lst[field])[0] else ''})
                continue
            if field not in fields_schema or not fields_get.get(fields_lst[field]):
                continue
            if fields_get.get(fields_lst[field]).get('type') == 'date':
                lang = self._context.get("lang")
                langs = self.env['res.lang']._lang_get(lang)
                date_format = langs.date_format or DATE_FORMAT
                res.update({field: str(record[fields_lst[field]].strftime(date_format)) if record[fields_lst[field]] else ''})
                continue
            if fields_get.get(fields_lst[field]).get('type') == 'datetime':
                lang = self._context.get("lang")
                langs = self.env['res.lang']._lang_get(lang)
                time_format = langs.time_format or DATETIME_FORMAT
                res.update({field: str(self.datetime_localize(record[fields_lst[field]], 'UTC', self.env.user.tz or 'Asia/Ho_Chi_Minh').strftime(time_format)) if record[fields_lst[field]] else ''})
                continue
            if fields_get.get(fields_lst[field]).get('type') == 'many2one':
                res.update({field: record[fields_lst[field]]['display_name'] if record[fields_lst[field]] else ''})
                continue
            if fields_get.get(fields_lst[field]).get('type') in ['many2many', 'one2many']:
                res.update({field: ','.join(record[fields_lst[field]].mapped('display_name')) if record[fields_lst[field]] else ''})
                continue
            if fields_get.get(fields_lst[field]).get('type') in ['float', 'integer', 'monetary', 'Percent']:
                res.update({field: record[fields_lst[field]] if record[fields_lst[field]] else 0.0})
                continue
            if fields_get.get(fields_lst[field]).get('type') == 'boolean':
                res.update({field: True if record[fields_lst[field]] else False})
                continue
            res.update({field: record[fields_lst[field]] if record[fields_lst[field]] else ''})

        return self.env.datamodels[model].load(res)
