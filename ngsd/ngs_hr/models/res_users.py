from odoo import models, fields, api, _


class ResUsers(models.Model):
    _inherit = "res.users"

    resume_line_ids = fields.One2many(readonly=True)
    employee_skill_ids = fields.One2many(readonly=True)
    leave_manager_id = fields.Many2one(readonly=True)
    address_id = fields.Many2one(readonly=True)
    work_location_id = fields.Many2one(readonly=True)
    resource_calendar_id = fields.Many2one(readonly=True)
    employee_parent_id = fields.Many2one(readonly=True)
    coach_id = fields.Many2one(readonly=True)
    mobile_phone = fields.Char(readonly=True)
    work_phone = fields.Char(readonly=True)
    indirect_manager = fields.Many2one(related='employee_id.indirect_manager')
    train_ctv = fields.Char(related='employee_id.train_ctv')
    job_code_id = fields.Many2one(related='employee_id.job_id.job_code_id')
    level_id = fields.Many2one(related='employee_id.level_id')
    sub_level_id = fields.Many2one(related='employee_id.sub_level_id')
    date_start_training = fields.Date(related='employee_id.date_start_training')
    date_end_training = fields.Date(related='employee_id.date_end_training')
    date_start_probation = fields.Date(related='employee_id.date_start_probation')
    date_end_probation = fields.Date(related='employee_id.date_end_probation')
    seniority_date = fields.Char(related='employee_id.seniority_date')
    rest_state = fields.Selection(related='employee_id.rest_state')
    departure_date = fields.Date(related='employee_id.departure_date')
    en_text_off = fields.Text(related='employee_id.en_text_off')
    en_day_layoff_from = fields.Date(related='employee_id.en_day_layoff_from')
    en_day_layoff_to = fields.Date(related='employee_id.en_day_layoff_to')
    en_text_layoff = fields.Text(related='employee_id.en_text_layoff')

    en_internal_ok = fields.Boolean(related='employee_id.en_type_id.internal_ok')
    address_current = fields.Char(related='employee_id.address_current', readonly=True)
    notebook_bhxh = fields.Char(related='employee_id.notebook_bhxh', readonly=True)
    tax_code = fields.Char(related='employee_id.tax_code', readonly=True)
    date_tax = fields.Date(related='employee_id.date_tax', readonly=True)
    place_tax = fields.Char(related='employee_id.place_tax', readonly=True)
    res_partner_bank_ids = fields.One2many(related='employee_id.res_partner_bank_ids', readonly=True)
    cccd_date = fields.Date(related='employee_id.cccd_date', readonly=True)
    cccd_place = fields.Char(related='employee_id.cccd_place', readonly=True)
    regular_address = fields.Char(related='employee_id.regular_address', readonly=True)
    depend_persion_id = fields.One2many(related='employee_id.depend_persion_id', readonly=True)
    work_permit_expiration_date = fields.Date(related='employee_id.work_permit_expiration_date', readonly=True)
    has_work_permit = fields.Binary(related='employee_id.has_work_permit', readonly=True)

    employee_country_id = fields.Many2one(readonly=True)
    identification_id = fields.Char(readonly=True)
    passport_id = fields.Char(readonly=True)
    gender = fields.Selection(readonly=True)
    place_of_birth = fields.Char(readonly=True)
    country_of_birth = fields.Many2one(readonly=True)
    private_email = fields.Char(readonly=True)
    phone = fields.Char(readonly=True)
    marital = fields.Selection(readonly=True)
    spouse_complete_name = fields.Char(readonly=True)
    spouse_birthdate = fields.Char(readonly=True)
    children = fields.Integer(readonly=True)
    emergency_contact = fields.Char(readonly=True)
    emergency_phone = fields.Char(readonly=True)
    visa_no = fields.Char(readonly=True)
    permit_no = fields.Char(readonly=True)
    visa_expire = fields.Date(readonly=True)
    birthday = fields.Date(readonly=True)
    private_lang = fields.Selection(readonly=True)
    job_title = fields.Char(readonly=True)
    work_email = fields.Char(readonly=True)

    shift = fields.Selection(related='employee_id.shift')
    has_child_start = fields.Date(related='employee_id.has_child_start')
    has_child_end = fields.Date(related='employee_id.has_child_end')
    check_timesheet_before_checkout = fields.Boolean(related='employee_id.check_timesheet_before_checkout')
    check_representative = fields.Boolean(related='employee_id.check_representative')
    lock_create_timesheet = fields.Datetime(related='employee_id.lock_create_timesheet')
    lock_approve_timesheet = fields.Datetime(related='employee_id.lock_approve_timesheet')
    lock_create_timesheet_exp = fields.Datetime(related='employee_id.lock_create_timesheet_exp')
    lock_approve_timesheet_exp = fields.Datetime(related='employee_id.lock_approve_timesheet_exp')

    @property
    def SELF_READABLE_FIELDS(self):
        work_info = ['leave_manager_id', 'address_id', 'indirect_manager', 'train_ctv', 'job_code_id', 'level_id', 'sub_level_id', 'date_start_training', 'date_end_training', 'date_start_probation', 'date_end_probation', 'seniority_date', 'rest_state', 'departure_date', 'en_text_off', 'en_day_layoff_from', 'en_day_layoff_to', 'en_text_layoff']
        persional_info = ['address_current', 'notebook_bhxh', 'tax_code', 'date_tax', 'place_tax', 'res_partner_bank_ids', 'cccd_date', 'cccd_place', 'regular_address', 'depend_persion_id', 'work_permit_expiration_date', 'has_work_permit']
        exists_persional_info = ['work_permit_expiration_date', 'notebook_bhxh', 'tax_code', 'date_tax', 'place_tax', 'phone', 'country_id', 'res_partner_bank_ids', 'depend_persion_id']
        hr_setting_info = ['shift', 'has_child_start', 'has_child_end', 'check_timesheet_before_checkout', 'check_representative', 'lock_create_timesheet', 'lock_approve_timesheet', 'lock_create_timesheet_exp', 'lock_approve_timesheet_exp']
        return super().SELF_READABLE_FIELDS + work_info + persional_info + exists_persional_info + hr_setting_info

    @property
    def SELF_WRITEABLE_FIELDS(self):
        res = super().SELF_WRITEABLE_FIELDS
        # Xoá các trường không cần thiết
        res = list(set(res).difference({'resume_line_ids', 'employee_skill_ids'}))
        return res
