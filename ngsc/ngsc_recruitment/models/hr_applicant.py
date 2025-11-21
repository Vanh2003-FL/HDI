import re
from datetime import datetime
import json
import logging

from odoo import models, fields, api, _, exceptions
from odoo.exceptions import ValidationError, UserError
from odoo import _
from odoo.exceptions import RedirectWarning

_logger = logging.getLogger(__name__)


class HrApplicant(models.Model):
    _inherit = "hr.applicant"

    email_from = fields.Char(required=True)
    name = fields.Char(string="Tên ứng viên")
    phone = fields.Char(string="Số điện thoại", size=32, required=True)
    yob = fields.Selection(selection='years_selection', string="Năm sinh", required=True, default='2000')
    gender = fields.Selection(string='Giới tính', selection=[
        ('male', 'Nam'),
        ('female', 'Nữ'),
    ], default='male', required=True)
    en_area_id = fields.Many2one(string='Khu vực', comodel_name='en.name.area')
    block_id = fields.Many2one(comodel_name="en.name.block", string="Khối", domain="[('area_id', '=', en_area_id)]")
    department_id = fields.Many2one(
        'hr.department',
        string="Trung tâm",
        domain="[('block_id', '=', block_id), ('block_id', '!=', False)]",
        compute=False,
        store=True,
        readonly=False,
    )
    en_department_id = fields.Many2one(comodel_name="en.department", string="Phòng ban",
                                       domain="[('department_id', '=', department_id)]")

    # Thông tin nghề nghiệp
    years_of_experience = fields.Integer(string="Số năm kinh nghiệm", required=True, default=1)
    education_level = fields.Selection(string='Trình độ học vấn', selection=[
        ('intermediate', 'Trung cấp'),
        ('college', 'Cao đẳng'),
        ('university', 'Đại học'),
        ('master', 'Thạc sĩ'),
        ('doctor', 'Tiến sĩ'),
        ('professor', 'Giáo sư')
    ], default='university', required=True)
    major = fields.Char(string='Chuyên ngành')
    certificates = fields.Many2many("hr.recruitment.certificate", string='Chứng chỉ')
    professional_competence = fields.Char('Năng lực chuyên môn')
    foreign_lang = fields.Many2many("hr.recruitment.foreign.lang", string='Trình độ ngoại ngữ')
    recent_work = fields.Char(string='Nơi làm việc gần đây')

    # Thông tin tuyển dụng
    employer_id = fields.Many2one(comodel_name="hr.employee",
                                  string="Người tuyển dụng",
                                  store=True,
                                  required=True,
                                  domain="[('en_department_id.code', '=', 'ĐBNL')]",
                                  default=lambda self: self.env.user.employee_id)
    skill_tag = fields.Many2many('ngsc.recruitment.skill.tag', relation='hr_applicant__skill_tag',
                                 string='Thẻ kỹ năng')
    news_job_id = fields.Many2one("ngsc.news.job", string="Vị trí công việc", tracking=True)
    apply_date = fields.Date(string='Ngày nộp hồ sơ')
    can_onboard_date = fields.Date(string='Ngày có thể nhận việc')
    worked_at_company = fields.Boolean(string='Đã từng làm việc tại công ty')
    currency_id = fields.Many2one("res.currency",
                                  string="Tiền tệ",
                                  default=lambda self: self.env['res.currency'].search([('name', '=', 'VND')], limit=1),
                                  store=True,
                                  required=True)
    salary_expect = fields.Monetary(string='Mức lương kỳ vọng', currency_field='currency_id')

    interview_booking_id = fields.Many2one(
        'calendar.event',
        string='Lịch phỏng vấn',
        help='Lịch phỏng vấn đã đặt cho ứng viên',
        copy=False,
        ondelete='set null'
    )

    # Thông tin người giới thiệu
    ref = fields.Many2one(comodel_name='hr.employee', string='Người giới thiệu',
                          relation='ngsc_recruitment_source_personnel__ref')
    department_ref = fields.Char(string="Đơn vị của người giới thiệu", readonly=True)
    email_ref = fields.Char(string='Email của người giới thiệu', readonly=True)
    bonus_ref = fields.Char(string='Thông tin trả thưởng')

    # Đánh giá ứng viên
    result = fields.Selection(selection=[
        ('pass', 'Đạt'),
        ('fail', 'Chưa đạt'),
    ], string='Kết quả đánh giá')

    resume = fields.Binary(string='Đính kèm CV', attachment=True)
    filename = fields.Char("Filename")

    candidate_evaluation = fields.Binary(string='File đánh giá ứng viên', attachment=True)
    filename_candidate_evaluation = fields.Char("Filename đánh giá ứng viên")

    hired_stage = fields.Boolean(related="stage_id.hired_stage", store=False)

    def get_default_interview_name(self):
        """Tạo tên buổi phỏng vấn mặc định"""
        if self.name and self.job_id:
            return f"Phỏng vấn {self.name} - {self.job_id.name}"
        elif self.name:
            return f"Phỏng vấn {self.name}"
        else:
            return "Buổi phỏng vấn"

    def _compute_stage(self):
        for applicant in self:
            if not applicant.stage_id:
                if self._context.get('website_id'):
                    stage = self.env['hr.recruitment.stage'].search([], order='sequence asc', limit=1)
                    applicant.stage_id = stage.id if stage else False
                else:
                    stages = self.env['hr.recruitment.stage'].search([], order='sequence asc')
                    if len(stages) >= 2:
                        applicant.stage_id = stages[1].id
                    else:
                        applicant.stage_id = stages[0].id if stages else False

    def years_selection(self):
        year_list = []
        for y in range(datetime.now().year - 80, datetime.now().year - 18):
            year_str = str(y)
            year_list.append((year_str, year_str))
        return year_list

    def _get_all_field_values(self):
        """Lấy tất cả giá trị của các field quan trọng"""
        field_values = {}
        important_fields = [
            'name', 'email_from', 'phone', 'yob', 'gender', 'years_of_experience',
            'education_level', 'major', 'professional_competence', 'recent_work',
            'salary_expect', 'result', 'apply_date', 'can_onboard_date',
            'worked_at_company', 'department_ref', 'email_ref', 'bonus_ref'
        ]

        for field in important_fields:
            if hasattr(self, field):
                value = getattr(self, field)
                if isinstance(value, models.BaseModel):
                    field_values[field] = {'id': value.id, 'name': value.name if hasattr(value, 'name') else str(value)}
                elif hasattr(value, 'ids'):
                    field_values[field] = [{'id': v.id, 'name': v.name if hasattr(v, 'name') else str(v)} for v in
                                           value]
                else:
                    field_values[field] = value

        many2one_fields = ['en_area_id', 'block_id', 'department_id', 'en_department_id',
                           'employer_id', 'news_job_id', 'ref', 'job_id', 'stage_id']

        for field in many2one_fields:
            if hasattr(self, field):
                value = getattr(self, field)
                if value:
                    field_values[field] = {'id': value.id, 'name': value.name if hasattr(value, 'name') else str(value)}
                else:
                    field_values[field] = None

        many2many_fields = ['certificates', 'foreign_lang', 'skill_tag']
        for field in many2many_fields:
            if hasattr(self, field):
                value = getattr(self, field)
                field_values[field] = [{'id': v.id, 'name': v.name if hasattr(v, 'name') else str(v)} for v in value]

        return field_values

    def _save_history(self, action_type='update'):
        """Lưu lịch sử với toàn bộ dữ liệu"""
        last_history = self.env['hr.applicant.edit.history'].search([
            ('applicant_id', '=', self.id)
        ], order='version desc', limit=1)

        new_version = (last_history.version + 1) if last_history else 1
        all_data = self._get_all_field_values()

        self.env['hr.applicant.edit.history'].create({
            'applicant_id': self.id,
            'version': new_version,
            'action_type': action_type,
            'edit_date': fields.Datetime.now(),
            'user_id': self.env.user.id,
            'data_snapshot': json.dumps(all_data, ensure_ascii=False, default=str),
            'applicant_name': self.name or '',
            'applicant_email': self.email_from or '',
        })

    @api.constrains('file', 'filename')
    def _check_file_type(self):
        for record in self:
            if record.filename:
                if not record.filename.lower().endswith('.pdf'):
                    raise ValidationError("CV chỉ được phép tải lên file PDF.")

    @api.onchange("en_area_id")
    def _onchange_area(self):
        if self.en_area_id:
            self.block_id = False
            self.department_id = False
            self.en_department_id = False

    @api.onchange("block_id")
    def _onchange_block_id(self):
        if self.block_id:
            self.department_id = False
            self.en_department_id = False

    @api.onchange("department_id")
    def _onchange_department_id(self):
        if self.department_id:
            self.en_department_id = False

    @api.onchange("ref")
    def onchange_ref(self):
        if self.ref:
            self.department_ref = self.ref.department_id.name
            self.email_ref = self.ref.work_email

    @api.onchange("name")
    def _onchange_name(self):
        self.partner_name = self.name

    @api.constrains('years_of_experience')
    def _check_years_of_experience(self):
        for record in self:
            if record.years_of_experience < 1 or record.years_of_experience >= 100:
                raise ValidationError("Số năm kinh nghiệm phải lớn hơn 1 và nhỏ hơn 100.")

    @api.constrains('email_from')
    def _validate_email(self):
        for record in self:
            match = re.match(r'^[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,4})$',
                             record.email_from)
            if not match:
                raise ValidationError('Email không đúng định dạng')

    @api.constrains('phone')
    def _validate_phone(self):
        for record in self:
            match = re.match(r"^(0|\+84|84)(3|5|7|8|9)[0-9]{8}$", record.phone)
            if not match:
                raise ValidationError('Số điện thoại không đúng định dạng')

    def _check_duplicate_email_and_redirect(self, email, exclude_id=None):
        domain = [
            ('email_from', '=', email),
            ('stage_id.sequence', '>=', 1)
        ]
        if exclude_id:
            domain.append(('id', '!=', exclude_id))

        existing_applicant = self.env['hr.applicant'].search(domain, limit=1)
        if existing_applicant:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            record_url = f"{base_url}/web#id={existing_applicant.id}&model=hr.applicant&view_type=form"

            action = {
                "type": "ir.actions.act_url",
                "target": "new",
                "url": record_url,
            }
            msg = _("Hồ sơ ứng viên đã tồn tại! Bạn có muốn mở hồ sơ này không?")
            raise RedirectWarning(msg, action, _("Xem hồ sơ"))

    @api.model
    def create(self, values):
        if values.get('email_from') and not self._context.get('website_id'):
            self._check_duplicate_email_and_redirect(values['email_from'])

        res = super(HrApplicant, self).create(values)

        if not res.stage_id:
            if self._context.get('website_id'):
                stage = self.env['hr.recruitment.stage'].search([], order='sequence asc', limit=1)
                if stage:
                    res.stage_id = stage.id
            else:
                stages = self.env['hr.recruitment.stage'].search([], order='sequence asc')
                if len(stages) >= 2:
                    res.stage_id = stages[1].id
                elif stages:
                    res.stage_id = stages[0].id

        res._save_history('create')

        if self._context.get('website_id', False) and res.news_job_id:
            res.job_id = res.news_job_id.job_id.id
            res.employer_id = res.news_job_id.create_uid.employee_id.id
            res._sent_mail_thank_you_for_apply()

        return res

    def write(self, values):
        for record in self:
            old_stage_seq = record.stage_id.sequence if record.stage_id else 0
            new_stage_id = values.get('stage_id')
            new_stage_seq = None
            if new_stage_id:
                new_stage = self.env['hr.recruitment.stage'].browse(new_stage_id)
                new_stage_seq = new_stage.sequence

            need_check = False

            if new_stage_seq is not None:
                if old_stage_seq == 0 and new_stage_seq >= 1:
                    need_check = True
                elif old_stage_seq >= 1 and new_stage_seq >= 1 and 'email_from' in values:
                    need_check = True
            elif old_stage_seq >= 1 and 'email_from' in values:
                need_check = True

            if need_check:
                email_to_check = values.get('email_from') or record.email_from
                if email_to_check:
                    self._check_duplicate_email_and_redirect(email_to_check, exclude_id=record.id)

        for record in self:
            record._save_history('update')

        return super(HrApplicant, self).write(values)

    def action_open_composer(self):
        """Mở form gửi email với context đầy đủ"""
        self.ensure_one()
        template_id = self.env['ir.model.data']._xmlid_to_res_id(
            'ngsc_recruitment.hr_applicant_invite_interview_02',
            raise_if_not_found=False
        )

        # Lấy dữ liệu từ lịch phỏng vấn hiện tại (nếu có)
        interview_start = self.interview_booking_id.start if self.interview_booking_id else False
        interview_stop = self.interview_booking_id.stop if self.interview_booking_id else False
        interview_room_id = self.interview_booking_id.room_id.id if getattr(self.interview_booking_id, 'room_id',
                                                                            False) else False
        interview_name = self.interview_booking_id.name if self.interview_booking_id else self.get_default_interview_name()

        # Context đầy đủ
        compose_ctx = dict(
            default_composition_mode='comment',
            default_model='hr.applicant',
            default_res_id=self.id,
            default_use_template=bool(template_id),
            default_template_id=template_id,
            default_partner_ids=[self.partner_id.id] if self.partner_id else [],
            # Fixed: removed Many2many command syntax

            # Dữ liệu ứng viên (cho template context)
            email=self.email_from,
            partner_name=self.partner_name,
            job_name=self.job_id.name if self.job_id else (self.news_job_id.name if self.news_job_id else ''),
            employer_name=self.employer_id.name if self.employer_id else '',
            employer_phone=self.employer_id.phone if self.employer_id else '',

            # Dữ liệu lịch phỏng vấn (default values cho form)
            default_interview_name=interview_name,
            default_interview_room_id=interview_room_id,
            default_interview_start=interview_start,
            default_interview_stop=interview_stop,
        )

        view_id = self.env.ref('ngsc_recruitment.ngsc_recruitment_email_compose_form').id

        return {
            'type': 'ir.actions.act_window',
            'name': 'Gửi email cho ứng viên',
            'res_model': 'mail.compose.message',
            'view_mode': 'form',
            'views': [(view_id, 'form')],
            'view_id': view_id,
            'target': 'new',
            'context': compose_ctx,
        }

    def _sent_mail_thank_you_for_apply(self):
        mail_template = self.env.ref('ngsc_recruitment.ngsc_recruitment_mail_template_001')
        mail_template.send_mail(self.id, force_send=True)

    def create_employee_from_applicant(self):
        for applicant in self:
            employee_data = {
                'default_name': applicant.partner_name or '',
                'default_job_id': applicant.job_id.id,
                'default_job_title': applicant.job_id.name,
                'default_en_area_id': applicant.en_area_id.id or False,
                'default_en_block_id': applicant.block_id.id or False,
                'default_en_department_id': applicant.en_department_id.id or False,
                'default_department_id': applicant.department_id.id or False,
                'default_address_id': applicant.company_id and applicant.company_id.partner_id
                                      and applicant.company_id.partner_id.id or False,
                'default_work_email': applicant.department_id and applicant.department_id.company_id
                                      and applicant.department_id.company_id.email or False,
                'default_work_phone': applicant.department_id.company_id.phone,
                'form_view_initial_mode': 'edit',
                'default_applicant_id': applicant.ids,
                'default_company_id': self.env.company.id
            }

            dict_act_window = self.env['ir.actions.act_window']._for_xml_id('hr.open_view_employee_list')
            dict_act_window.update({
                'view_mode': 'form',
                'views': [(False, 'form')],
                'target': 'current',
                'context': employee_data
            })
            return dict_act_window


class HrApplicantEditHistory(models.Model):
    """Model để lưu lịch sử chỉnh sửa hồ sơ với toàn bộ dữ liệu"""
    _name = 'hr.applicant.edit.history'
    _description = 'Lịch sử chỉnh sửa hồ sơ ứng viên'
    _order = 'version desc'

    applicant_id = fields.Many2one('hr.applicant', string='Hồ sơ ứng viên', required=True, ondelete='cascade')
    version = fields.Integer(string='Phiên bản', required=True)
    action_type = fields.Selection([
        ('create', 'Tạo mới'),
        ('update', 'Cập nhật')
    ], string='Loại thao tác', required=True)
    edit_date = fields.Datetime(string='Ngày chỉnh sửa', required=True, default=fields.Datetime.now)
    user_id = fields.Many2one('res.users', string='Người thực hiện', required=True)

    data_snapshot = fields.Text(string='Snapshot dữ liệu', required=True)

    applicant_name = fields.Char(string='Tên ứng viên')
    applicant_email = fields.Char(string='Email ứng viên')

    @api.model
    def create(self, values):
        if not values.get('user_id'):
            values['user_id'] = self.env.user.id
        return super(HrApplicantEditHistory, self).create(values)

    def get_data_as_dict(self):
        """Chuyển đổi data_snapshot từ JSON thành dict"""
        try:
            return json.loads(self.data_snapshot)
        except:
            return {}

    def action_view_snapshot(self):
        """Action để xem chi tiết snapshot"""
        data = self.get_data_as_dict()

        formatted_data = ""
        for field, value in data.items():
            if isinstance(value, dict) and 'name' in value:
                formatted_data += f"{field}: {value['name']}\n"
            elif isinstance(value, list):
                names = [item.get('name', str(item)) if isinstance(item, dict) else str(item) for item in value]
                formatted_data += f"{field}: {', '.join(names)}\n"
            else:
                formatted_data += f"{field}: {value}\n"

        return {
            'type': 'ir.actions.act_window',
            'name': f'Chi tiết phiên bản {self.version}',
            'res_model': 'hr.applicant.edit.history',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {'formatted_data': formatted_data}
        }


class HrApplicantSearch(models.TransientModel):
    _name = 'hr.applicant.search'
    _description = 'Tìm kiếm hồ sơ ứng viên'

    name = fields.Char(string='Tên')
    en_area_id = fields.Many2one('en.name.area', string='Khu vực')
    block_id = fields.Many2one(comodel_name="en.name.block", string="Khối")
    department_id = fields.Many2one(comodel_name="hr.department", string="Trung tâm")
    en_department_id = fields.Many2one(comodel_name="en.department", string="Phòng ban")
    job_position = fields.Many2one('hr.job', string='Vị trí công việc')
    years_of_experience = fields.Integer(string='Số năm kinh nghiệm')
    skill_tag = fields.Many2many('ngsc.recruitment.skill.tag',
                                 relation='hr_applicant_search__skill_tag',
                                 string='Thẻ kỹ năng')

    def action_search_personnel(self):
        domain = []
        if self.name:
            domain.append(('name', 'ilike', self.name))
        if self.en_area_id:
            domain.append(('en_area_id', '=', self.en_area_id.id))
        if self.block_id:
            domain.append(('block_id', '=', self.block_id.id))
        if self.department_id:
            domain.append(('department_id', '=', self.department_id.id))
        if self.en_department_id:
            domain.append(('en_department_id', '=', self.en_department_id.id))
        if self.job_position:
            domain.append(('job_position', '=', self.job_position.id))
        if self.skill_tag:
            domain.append(('skill_tag', 'in', self.skill_tag.ids))
        if self.years_of_experience:
            domain.append(('years_of_experience', '>=', self.years_of_experience))

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ngsc.recruitment.source.personnel',
            'view_mode': 'tree,form',
            'views': [(False, 'tree'), (False, 'form')],
            'target': 'current',
            'domain': domain,
        }


class HrRecruitmentCertificate(models.Model):
    _name = 'hr.recruitment.certificate'
    _description = 'Chứng chỉ'

    name = fields.Char(string="Tên chứng chỉ", required=True)
    sequence = fields.Integer("Số thứ tự", default=1)


class HrRecruitmentForeignLang(models.Model):
    _name = 'hr.recruitment.foreign.lang'
    _description = 'Trình độ ngoại ngữ'

    name = fields.Char(string="Tên trình độ ngoại ngữ", required=True)
    sequence = fields.Integer("Số thứ tự", default=1)


class CalendarEventInherit(models.Model):
    _inherit = "calendar.event"

    def _sync_activities(self, fields=None):
        """Đồng bộ với activities nhưng loại bỏ các field không hợp lệ"""
        if self._context.get('skip_activity_sync'):
            return

        try:
            activity_model = self.env['mail.activity']
            valid_activity_fields = set(activity_model._fields.keys())
        except Exception:
            valid_activity_fields = {
                'id', 'create_date', 'write_date', 'create_uid', 'write_uid',
                'res_model', 'res_id', 'activity_type_id', 'summary', 'note',
                'date_deadline', 'user_id', 'request_partner_id', 'state',
                'feedback', 'previous_activity_type_id', 'calendar_event_id'
            }

        excluded_fields = {
            'room_id', 'location', 'videocall_location',
            'recurrency', 'rrule', 'end_type', 'count',
            'interval', 'until', 'month_by', 'weekday',
            'byday', 'day', 'show_as', 'privacy', 'allday',
            'start', 'stop', 'duration', 'partner_ids'
        }

        for event in self:
            if not event.activity_ids:
                continue

            activity_values = {}

            if not fields or 'name' in fields:
                activity_values['summary'] = event.name

            if not fields or 'description' in fields:
                activity_values['note'] = event.description or ''

            if not fields or 'start' in fields:
                activity_values['date_deadline'] = event.start.date() if event.start else False

            if not fields or 'user_id' in fields:
                activity_values['user_id'] = event.user_id.id if event.user_id else False

            filtered_values = {
                key: value for key, value in activity_values.items()
                if key in valid_activity_fields and key not in excluded_fields
            }

            if filtered_values:
                try:
                    event.activity_ids.write(filtered_values)
                except Exception as e:
                    _logger.warning(
                        "Failed to sync activities for calendar event %s: %s",
                        event.id, str(e)
                    )

    def unlink(self):
        """Xóa event và xóa tham chiếu trong applicant"""
        applicants = self.env['hr.applicant'].search([('interview_booking_id', 'in', self.ids)])
        applicants.write({'interview_booking_id': False})
        return super(CalendarEventInherit, self).unlink()


class MailComposeMessageInherit(models.TransientModel):
    _inherit = 'mail.compose.message'

    interview_name = fields.Char(string="Tên buổi phỏng vấn")
    interview_room_id = fields.Many2one('room.room', string="Phòng phỏng vấn")
    interview_start = fields.Datetime(string="Thời gian phỏng vấn")
    interview_stop = fields.Datetime(string="Kết thúc phỏng vấn")

    has_existing_booking = fields.Boolean(string="Đã có lịch phỏng vấn", default=False)
    existing_booking_info = fields.Char(string="Thông tin lịch hiện tại", default="")

    formatted_interview_time = fields.Char(
        string="Formatted Interview Time",
        compute="_compute_formatted_time"
    )

    @api.model
    def default_get(self, fields_list):
        res = super(MailComposeMessageInherit, self).default_get(fields_list)
        applicant_id = self._context.get('default_res_id') or self._context.get('applicant_id')
        model_name = self._context.get('default_model') or self._context.get('model')

        if model_name == 'hr.applicant' and applicant_id:
            applicant = self.env['hr.applicant'].browse(applicant_id)
            if applicant.interview_booking_id:
                event = applicant.interview_booking_id
                res.update({
                    'has_existing_booking': True,
                    'existing_booking_info': f"Phòng: {event.room_id.name if event.room_id else 'Không xác định'} - "
                                             f"Thời gian: {event.start.strftime('%d/%m/%Y %H:%M') if event.start else ''}",
                })
            else:
                res.update({'has_existing_booking': False})
        return res

    @api.depends('interview_start', 'interview_stop')
    def _compute_formatted_time(self):
        for record in self:
            if record.interview_start and record.interview_stop:
                start_time = fields.Datetime.context_timestamp(record, record.interview_start)
                stop_time = fields.Datetime.context_timestamp(record, record.interview_stop)
                record.formatted_interview_time = f"{start_time.strftime('%H:%M')} - {stop_time.strftime('%H:%M')}, {start_time.strftime('%d/%m/%Y')}"
            else:
                record.formatted_interview_time = ""

    @api.onchange('interview_name', 'interview_room_id', 'interview_start', 'interview_stop', 'template_id')
    def _onchange_interview_fields(self):
        """Cập nhật preview email khi thay đổi thông tin phỏng vấn"""
        # Nếu chưa chọn template thì bỏ qua
        if not self.template_id:
            return

        # Lấy template mời phỏng vấn
        interview_template = self.env.ref(
            'ngsc_recruitment.hr_applicant_invite_interview_02',
            raise_if_not_found=False
        )
        if not interview_template or self.template_id.id != interview_template.id:
            return

        # Lấy ứng viên
        applicant = None
        if self.model == 'hr.applicant' and self.res_id:
            applicant = self.env['hr.applicant'].browse(self.res_id)
        if not applicant:
            return

        try:
            # Tạo context với dữ liệu cập nhật từ form
            render_ctx = {
                # Dữ liệu phỏng vấn từ form (ưu tiên)
                'interview_start': self.interview_start,
                'interview_stop': self.interview_stop,
                'interview_room_id': self.interview_room_id,
                'interview_room_name': self.interview_room_id.name if self.interview_room_id else '',

                # Dữ liệu ứng viên
                'email': applicant.email_from,
                'partner_name': applicant.partner_name,
                'job_name': applicant.job_id.name if applicant.job_id else '',
                'employer_name': applicant.employer_id.name if applicant.employer_id else '',
                'employer_phone': applicant.employer_id.phone if applicant.employer_id else '',
            }

            # Merge context
            full_ctx = {
                **self.env.context,
                **render_ctx,
                'ctx': render_ctx,  # QUAN TRỌNG: Thêm ctx để template có thể access
            }

            # Render subject và body với context đầy đủ
            record_id = applicant.id

            subject_render = self.template_id.with_context(**full_ctx)._render_field(
                'subject',
                [record_id]
            )
            body_render = self.template_id.with_context(**full_ctx)._render_field(
                'body_html',
                [record_id]
            )

            # Cập nhật vào form
            self.subject = subject_render.get(record_id, '')
            self.body = body_render.get(record_id, '')
            self.can_edit_body = True

        except Exception as e:
            _logger.error(f"Error rendering interview email template: {str(e)}")
            raise UserError(_("Không thể hiển thị nội dung email phỏng vấn: %s") % str(e))

    def action_send_mail(self):
        self.ensure_one()

        if self.model == 'hr.applicant' and self.res_id:
            template = self.env.ref('ngsc_recruitment.hr_applicant_invite_interview_02', raise_if_not_found=False)
            if template and self.template_id and self.template_id.id == template.id:
                if not all([self.interview_name, self.interview_room_id, self.interview_start, self.interview_stop]):
                    raise UserError(_(
                        "Vui lòng nhập đầy đủ thông tin lịch phỏng vấn trước khi gửi email:\n"
                        "- Tên buổi phỏng vấn\n"
                        "- Phòng phỏng vấn\n"
                        "- Thời gian bắt đầu\n"
                        "- Thời gian kết thúc"
                    ))

                if self.interview_start >= self.interview_stop:
                    raise UserError(_("Thời gian bắt đầu phải nhỏ hơn thời gian kết thúc."))

                applicant = self.env['hr.applicant'].browse(self.res_id)

                domain = [
                    ('room_id', '=', self.interview_room_id.id),
                    ('start', '<', self.interview_stop),
                    ('stop', '>', self.interview_start)
                ]
                if applicant.interview_booking_id:
                    domain.append(('id', '!=', applicant.interview_booking_id.id))

                overlapping_events = self.env['calendar.event'].search(domain)
                if overlapping_events:
                    conflicting_names = overlapping_events.mapped('name')
                    raise UserError(_(
                        "Phòng %s đã được đặt trong khoảng thời gian này.\nCác lịch trùng:\n%s"
                    ) % (self.interview_room_id.name, '\n'.join(f"- {name}" for name in conflicting_names)))

                try:
                    self._sync_to_calendar_event()
                except Exception as e:
                    _logger.error(f"Error syncing to calendar event: {str(e)}")
                    raise UserError(_("Không thể đặt lịch phỏng vấn. Lỗi: %s") % str(e))

        result = super(MailComposeMessageInherit, self).action_send_mail()
        return result

    def _sync_to_calendar_event(self):
        self.ensure_one()

        if self.model != 'hr.applicant' or not self.res_id:
            return

        applicant = self.env['hr.applicant'].browse(self.res_id)

        partner_ids = [self.env.user.partner_id.id]
        if applicant.partner_id:
            partner_ids.append(applicant.partner_id.id)

        event_data = {
            'name': self.interview_name,
            'start': self.interview_start,
            'stop': self.interview_stop,
            'user_id': self.env.user.id,
            'partner_ids': [(6, 0, partner_ids)],
        }

        if hasattr(self.env['calendar.event'], 'room_id'):
            event_data['room_id'] = self.interview_room_id.id

        if applicant.interview_booking_id:
            applicant.interview_booking_id.with_context(skip_activity_sync=True).write(event_data)
            _logger.info(f"Updated calendar event {applicant.interview_booking_id.id} for applicant {applicant.name}")
        else:
            event_data.update({
                'res_model': 'hr.applicant',
                'res_id': applicant.id,
                'show_as': 'busy',
                'privacy': 'public',
            })

            event = self.env['calendar.event'].with_context(
                skip_activity_sync=True,
                mail_create_nolog=True,
                mail_create_nosubscribe=True
            ).create(event_data)

            applicant.write({'interview_booking_id': event.id})
            _logger.info(f"Created new calendar event {event.id} for applicant {applicant.name}")

        self.write({
            'has_existing_booking': True,
            'existing_booking_info': f"Phòng: {self.interview_room_id.name} - Thời gian: {self.interview_start.strftime('%d/%m/%Y %H:%M')}"
        })
