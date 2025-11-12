from odoo.addons.component.core import Component
from odoo.tools.safe_eval import safe_eval
# from odoo.addons.base_rest_datamodel.restapi import Datamodel
from odoo import fields, exceptions, _
from odoo.addons.base_rest.components.service import to_bool, to_int
from pytz import timezone, UTC
from odoo.addons.base_rest import restapi
from dateutil.relativedelta import relativedelta
from datetime import timedelta, datetime, time
from .fields_list import *
import logging
log = logging.getLogger(__name__)
from odoo.http import request
from odoo.exceptions import UserError, AccessError, ValidationError
import json
from odoo.tools import date_utils


def validate_params(params, valid):
    for key in valid.keys():
        if hasattr(params, key) and getattr(params, key) != valid[key]:
            return False, key, getattr(params, key)
    return True, '', ''


class PowerBiService(Component):
    _inherit = "base.rest.service"
    _name = "powerbi.service.info"
    _usage = "v1"
    _collection = "all.rest.api.services"
    _description = """NGS CRM Services"""
    _log_calls_in_db = True

    @restapi.method(
        [(["/getProjectResourceData"], "GET")]
    )
    def getProjectResourceData(self):
        records = self.env["get.project.resource.data"].search([])
        datas = [{
            'Center': record.department_id,
            'Opp/Project': record.type_project,
            'Status': record.status,
            'Project_ID': record.project_id,
            'Project type': record.project_type,
            'Các loại tiêu chí': record.type,
            'Tổng': record.total,
            'Lũy Kế tháng báo cáo': record.all_total,
            'Tháng': record.month_text,
            'Năm': record.year_text,
            'Ngày': record.date_text,
            'Giá trị': record.value,
        } for record in records]
        return datas

    @restapi.method(
        [(["/getCenterData"], "GET")]
    )
    def getCenterData(self):
        records = self.env["get.center.data"].search([])
        datas = [{
            'Trung tâm': record.department_id,
            'Chỉ số': record.type,
            'Tháng': record.month_text,
            'Năm': record.year_text,
            'Ngày': record.date_text,
            'Giá trị': record.value,
        } for record in records]
        return datas

    @restapi.method(
        [(["/getSlideData"], "GET")]
    )
    def getSlideData(self):
        records = self.env["get.slide.data"].search([])
        datas = [{
            'Trung tâm': record.department_id,
            'Chỉ số': record.option,
            'Loại': record.type,
            'Tháng': record.month_text,
            'Năm': record.year_text,
            'Ngày': record.date_text,
            'Giá trị': record.value,
        } for record in records]
        return datas

    @restapi.method(
        [(["/getTableCriteria"], "GET")]
    )
    def getTableCriteria(self):
        table_criteria_api = self.env["table.criteria.api"].search([])
        options = []
        for criteria in table_criteria_api:
            options.append({
                'TieuChiLv1': criteria.criteria_lv1,
                'TieuChiLv2': criteria.criteria_lv2,
                'ID': criteria.id
            })
        return options

    @restapi.method(
        [(["/getDimDate"], "GET")]
    )
    def getDimDate(self):
        options = []
        date_from = datetime.now() + relativedelta(years=-1, month=1, day=1)
        date_to = datetime.now() + relativedelta(years=1, days=-1, month=1, day=1)
        for date_step in date_utils.date_range(date_from, date_to, relativedelta(days=1)):
            compared_from = date_step
            options.append({
                'Ngày': compared_from.strftime('%d/%m/%Y'),
                'Tháng': compared_from.month,
                'Tháng T': f'T{compared_from.month}',
                'Tháng_full': f'Tháng {compared_from.month}',
                'Quý': f'Quý {date_utils.get_quarter_number(compared_from)}',
                'Năm': compared_from.year,
            })
        return options

    @restapi.method(
        [(["/getCenterId"], "GET")]
    )
    def getCenterId(self):
        center_ids = self.env["hr.department"].search([])
        options = []
        for center in center_ids:
            options.append({
                'Tên': center.display_name or '',
                'ID': center.id
            })
        return options


