from odoo import models, api, fields
from datetime import timedelta, datetime, time
from dateutil.relativedelta import relativedelta


class GetProjectResourceData(models.Model):
    _name = "get.project.resource.data"

    department_id = fields.Integer('Center')
    type_project = fields.Char('Opp/Project')
    status = fields.Char('Status')
    project_id = fields.Char('Project_ID')
    project_type = fields.Char('Project type')
    type = fields.Char('Các loại tiêu chí')
    total = fields.Float('Tổng')
    all_total = fields.Float('Lũy Kế tháng báo cáo')
    month_text = fields.Char('Tháng')
    year_text = fields.Char('Năm')
    date_text = fields.Char('Ngày')
    value = fields.Float('Giá trị')

    def refresh_data(self):
        self.search([]).unlink()
        options = {
            'date': {
                'date_from': datetime.today() + relativedelta(years=-1, month=1, day=1),
                'date_to': datetime.today() + relativedelta(years=1, days=-1, month=1, day=1),
            }
        }
        datas = self.env["project.resource.account.report"]._get_lines_report_api(options)
        for d in datas:
            self.create({
                'department_id': d.get('Center'),
                'type_project': d.get('Opp/Project'),
                'status': d.get('Status'),
                'project_id': d.get('Project_ID'),
                'project_type': d.get('Project type'),
                'type': d.get('Các loại tiêu chí'),
                'total': d.get('Tổng'),
                'all_total': d.get('Lũy Kế tháng báo cáo'),
                'month_text': d.get('Tháng'),
                'year_text': d.get('Năm'),
                'date_text': d.get('Ngày'),
                'value': d.get('Giá trị'),
            })


class GetCenterData(models.Model):
    _name = "get.center.data"

    department_id = fields.Integer('Trung tâm')
    type = fields.Char('Chỉ số')
    month_text = fields.Char('Tháng')
    year_text = fields.Char('Năm')
    date_text = fields.Char('Ngày')
    value = fields.Float('Giá trị')

    def refresh_data(self):
        self.search([]).unlink()
        options = {
            'date': {
                'date_from': datetime.today() + relativedelta(years=-1, month=1, day=1),
                'date_to':  datetime.today() + relativedelta(years=1, days=-1, month=1, day=1),
            }
        }
        datas = self.env["department.resource.account.report"]._get_lines_report_api(options)
        for d in datas:
            self.create({
                'department_id': d.get('Trung tâm'),
                'type': d.get('Chỉ số'),
                'month_text': d.get('Tháng'),
                'year_text': d.get('Năm'),
                'date_text': d.get('Ngày'),
                'value': d.get('Giá trị'),
            })


class GetSlideData(models.Model):
    _name = "get.slide.data"

    department_id = fields.Integer('Trung tâm')
    type = fields.Char('Loại')
    option = fields.Char('Chỉ số')
    month_text = fields.Char('Tháng')
    year_text = fields.Char('Năm')
    date_text = fields.Char('Ngày')
    value = fields.Float('Giá trị')

    def refresh_data(self):
        self.search([]).unlink()
        options = {
            'date': {
                'date_from': datetime.today() + relativedelta(years=-1, month=1, day=1),
                'date_to':  datetime.today() + relativedelta(years=1, days=-1, month=1, day=1),
            }
        }
        datas = self.env["project.resource.account.report"]._get_lines_report_slide_api(options)
        for d in datas:
            self.create({
                'department_id': d.get('Trung tâm'),
                'type': d.get('Loại'),
                'option': d.get('Chỉ số'),
                'month_text': d.get('Tháng'),
                'year_text': d.get('Năm'),
                'date_text': d.get('Ngày'),
                'value': d.get('Giá trị'),
            })
