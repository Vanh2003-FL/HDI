from odoo import models, api, fields, _, exceptions
import xlrd, xlsxwriter
from datetime import datetime
import io
import base64
from dateutil.relativedelta import relativedelta
import time, math, pytz
from pytz import timezone, utc
from odoo.exceptions import UserError
from odoo.tools.mimetypes import guess_mimetype


import logging

_logger = logging.getLogger(__name__)

datemode = 0

from os import listdir
from os.path import isfile, join, isdir


class ImportMigratePopup(models.TransientModel):
    _name = 'import.migrate.popup'

    def import_data(self, folder):
        import_info = ['employee.xlsx', 'project.xlsx', 'khnl.xlsx', 'WBS', 'ruiro.xlsx', 'vande.xlsx', 'TS_OT', 'bangiao.xlsx', 'taichinh.xlsx']

        for f in import_info:
            if isfile(join(folder, f)):
                file = open(join(folder, f), mode="rb").read()
                self.batch_import_file(file, type=f)
            else:
                new_folder = join(folder, f)
                for af in listdir(new_folder):
                    if isfile(join(new_folder, af)):
                        self.batch_import_file(file, type=f.lower())

    def sync_folder_data(self, path, name, project, parent=False):
        _logger.info(f'Trying {path}')
        if not isdir(path):
            _logger.info(f'not found path {path}')
            return
        folder = self.create_folder(name, project, parent)
        for c in listdir(path):
            if isfile(join(path, c)):
                file = open(join(path, c), mode="rb").read()
                self.create_file_data(file, folder, c)
            else:
                new_path = join(path, c)
                self.sync_folder_data(new_path, c, project, folder)
        _logger.info(f'Done {path}')

    def create_folder(self, name, project, parent=False):
        parent = parent or self.env["documents.folder"]
        exist = self.env["documents.folder"].search([('name', '=', name), ('en_project_id', '=', project.id), ('parent_folder_id', '=', parent.id)], limit=1)
        if exist:
            return exist
        value = {
            "name": name,
            "en_project_id": project.id,
            "parent_folder_id": parent.id,
            "en_if_project": False,
            "company_id": False,
            "facet_ids": [],
            "group_ids": [[6, 0, []]],
            "user_specific_write": False,
            "read_group_ids": [[6, 0, []]],
            "user_specific": False,
            "description": "<p></p>"
        }
        f = self.env["documents.folder"].create(value)
        f.self_onchange_parent_folder_id()
        return f

    def create_file_data(self, file, folder, filename):
        if self.env['documents.document'].search([('name', '=', filename), ('folder_id', '=', folder.id)]):
            return
        mimetype = guess_mimetype(file or b'')
        document_dict = {
            'mimetype': mimetype,
            'name': filename,
            'datas': base64.b64encode(file),
            'tag_ids': [(6, 0, [])],
            'folder_id': folder.id,
        }
        return self.env['documents.document'].with_context(binary_field_real_user=self.env.user).create(document_dict)

    def batch_import_file(self, file, type):
        stage_import = self.env['base_import.import'].create({
            'res_model': 'hr.employee',
            'file': file,
            'file_name': 'employee.xlsx',
            'file_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        file_length, rows = stage_import._read_file({})
        if type == 'employee.xlsx':
            to_header = 1
            headers = []
            if to_header:
                for h in range(to_header):
                    headers = rows.pop(h)
            _logger.info('File: %s, importing %d rows...' % (type, len(rows)))
            i = 0
            Employee = self.env['hr.employee']
            for row in rows:
                i += 1
                unit = row[5]
                dta = unit.split('/')
                address_id = en_area_id = en_block_id = department_id = en_department_id = False
                for d in dta:
                    if d == 'NGS Consulting (NGSC)':
                        address_id = 1
                    elif 'Khối' in d:
                        en_block_id = Employee.en_block_id.convert_m2o_from_name(d.replace('Khối ', ''))
                    elif 'Phòng' in d:
                        en_department_id = Employee.en_department_id.convert_m2o_from_name(d.replace('Phòng ', ''))
                    elif 'Trung tâm' in d or 'Ban' in d:
                        department_id = Employee.department_id.convert_m2o_from_name(d.replace('Trung tâm ', '').replace('Ban ', ''))
                    elif f"{d}/Khối" in unit:
                        en_area_id = Employee.en_area_id.convert_m2o_from_name(d)
                    elif f"{d}/Phòng" in unit:
                        department_id = Employee.department_id.convert_m2o_from_name(d)
                    else:
                        department_id = Employee.department_id.convert_m2o_from_name(d)
                vals = {
                    'name': row[0],
                    'barcode': row[1],
                    'work_email': row[3],
                    'job_id': self.env['hr.job'].convert_m2o_from_name(row[4]),
                    'en_area_id': en_area_id,
                    'en_block_id': en_block_id,
                    'department_id': department_id,
                    'en_department_id': en_department_id,
                    'address_id': address_id,
                    'en_date_start': row[6] or False,
                    'departure_date': row[7] or False,
                }
                xmlid = '__import__.hr_employee_' + row[2]
                data = dict(xml_id=xmlid, values=vals, noupdate=False)
                if self.env['res.users'].with_context(active_test=False).search([('login', '=', row[3])]):
                    _logger.info('File: %s, Error %s row at %s/%s' % (type, str('trùng email %s'%row[3]), i, len(rows)))
                    continue
                employee = Employee.sudo()._load_records([data])
                Employee.env.cr.commit()
                _logger.info('File: %s, Imported %s row at %s/%s' % (type, employee.id, i, len(rows)))
        if type == 'project.xlsx':
            to_header = 1
            headers = []
            if to_header:
                for h in range(to_header):
                    headers = rows.pop(h)
            _logger.info('File: %s, importing %d rows...' % (type, len(rows)))
            i = 0
            Project = self.env['project.project']
            for row in rows:
                i += 1
                unit = row[5]
                dta = unit.split('/')
                address_id = en_area_id = en_block_id = department_id = en_department_id = False
                for d in dta:
                    if d == 'NGS Consulting (NGSC)':
                        address_id = 1
                    elif 'Khối' in d:
                        en_block_id = Employee.en_block_id.convert_m2o_from_name(d.replace('Khối ', ''))
                    elif 'Phòng' in d:
                        en_department_id = Employee.en_department_id.convert_m2o_from_name(d.replace('Phòng ', ''))
                    elif 'Trung tâm' in d or 'Ban' in d:
                        department_id = Employee.department_id.convert_m2o_from_name(d.replace('Trung tâm ', '').replace('Ban ', ''))
                    elif f"{d}/Khối" in unit:
                        en_area_id = Employee.en_area_id.convert_m2o_from_name(d)
                    elif f"{d}/Phòng" in unit:
                        department_id = Employee.department_id.convert_m2o_from_name(d)
                    else:
                        department_id = Employee.department_id.convert_m2o_from_name(d)
                match = {
                  "1": [
                    "en_code"
                  ],
                  "2": [
                    "name"
                  ],
                  "4": [
                    "en_project_type_id"
                  ],
                  "5": [
                    "en_list_project_id"
                  ],
                  "6": [
                    "en_project_model_id"
                  ],
                  "7": [
                    "stage_id"
                  ],
                  "8": [
                    "en_customer_type_id"
                  ],
                  "9": [
                    "partner_id"
                  ],
                  "10": [
                    "en_contract_type_id"
                  ],
                  "11": [
                    "en_contract_number"
                  ],
                  "12": [
                    "en_branch_id"
                  ],
                  "14": [
                    "currency_id"
                  ],
                  "15": [
                    "en_department_id"
                  ],
                  "16": [
                    "en_project_manager_id"
                  ],
                  "18": [
                    "en_bmm_ids"
                  ],
                  "21": [
                    "user_id"
                  ],
                  "23": [
                    "en_project_qa_id"
                  ],
                  "25": [
                    "date_start"
                  ],
                  "26": [
                    "date"
                  ],
                  "29": [
                    "en_link_system"
                  ],
                  "30": [
                    "description"
                  ],
                  "31": [
                    "privacy_visibility"
                  ]
                }
                xmlid = row[0]
                data = dict(xml_id=xmlid, values=vals, noupdate=False)
                employee = Employee.sudo()._load_records([data])
                Employee.env.cr.commit()
                _logger.info('File: %s, Imported %s row at %s/%s' % (type, employee.id, i, len(rows)))

