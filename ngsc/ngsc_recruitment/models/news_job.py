import unicodedata
from odoo import models, fields, api
from odoo.tools.translate import html_translate
from odoo.exceptions import ValidationError


class NewsJob(models.Model):
    _name = "ngsc.news.job"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "id desc"
    _description = "Tin tuyển dụng"

    def _get_default_favorite_user_ids(self):
        return [(6, 0, [self.env.uid])]

    def _get_default_website_description(self):
        default_description = self.env.ref("website_hr_recruitment.default_website_description",
                                           raise_if_not_found=False)
        return default_description._render() if default_description else ""

    name = fields.Char(string="Tin tuyển dụng", required=True, tracking=True)
    short_name = fields.Char(string="Tên viết tắt", compute="_compute_short_name", index=True, store=True)
    description = fields.Html(string="Mô tả", required=True, tracking=True)
    color = fields.Integer("Color Index", tracking=True)
    create_uid = fields.Many2one("res.users", string="Người tạo", default=lambda self: self.env.user)
    is_favorite = fields.Boolean(compute="_compute_is_favorite", inverse="_inverse_is_favorite")
    favorite_user_ids = fields.Many2many("res.users", "news_job_favorite_user_rel", "news_job_id", "user_id",
                                         default=_get_default_favorite_user_ids, copy=False)
    state = fields.Selection(string="Trạng thái", tracking=True, default="recruit", copy=False,
                             selection=[("recruit", "Đang tuyển dụng"),
                                        ("open", "Dừng tuyển dụng")])
    job_id = fields.Many2one( string="Vị trí ứng tuyển", required=True, related='plan_id.request_id.job_position',store=True,)
    date_start = fields.Date(string="Ngày bắt đầu tuyển", required=True, tracking=True)
    date_end = fields.Date(string="Ngày kết thúc tuyển", required=True, tracking=True)
    website_url = fields.Char(string="Đường dẫn website tin tuyển dụng", compute="_compute_website_url")
    news_job_url = fields.Char(string="Link URL", compute="_compute_website_url")
    is_published = fields.Boolean(string="Đã đăng", default=False, tracking=True, copy=False)
    datetime_published = fields.Datetime(string="Ngày đăng", tracking=True)
    hr_applicant_ids = fields.One2many("hr.applicant", "news_job_id", string="Hồ sơ ứng viên")
    appraisal_count = fields.Integer(string="Thẩm định ban đầu", compute="_compute_count_applicant", store=True,
                                     help="Số lượng hồ sơ ứng viên đang thẩm định")
    interview_count = fields.Integer(string="Phỏng vấn", compute="_compute_count_applicant", store=True,
                                     help="Số lượng hồ sơ ứng viên đang phỏng vấn")
    contract_proposal_count = fields.Integer(string="Đề xuất hợp đồng", compute="_compute_count_applicant", store=True,
                                             help="Số lượng hồ sơ đang đề xuất hợp đồng")
    contract_signed_count = fields.Integer(string="Hợp đồng đã ký", compute="_compute_count_applicant", store=True,
                                           help="Số lượng hồ sơ ứng viên đã ký hợp đồng")
    no_of_recruitment = fields.Integer(string="Số lượng hồ sơ cần tuyển", required=True, related='plan_id.request_id.job_quantity')
    all_application_count = fields.Integer(string="Hồ sơ ứng tuyển", compute="_compute_all_application_count",)
    new_application_count = fields.Integer(string="Hồ sơ ứng tuyển mới", compute="_compute_state_new_application_count",)
    old_application_count = fields.Integer(string="Hồ sơ ứng tuyển cũ",compute="_compute_old_application_count",)

    no_of_hired_employee = fields.Integer(default=0, compute="_compute_no_of_hired_employee")
    application_count = fields.Integer(string="Hồ sơ ứng tuyển",  compute="_compute_application_count",)
    website_description = fields.Html('Website description', translate=html_translate, sanitize_attributes=False,
                                      default=_get_default_website_description, prefetch=False, sanitize_form=False)
    active = fields.Boolean(string="Hoạt động", default=True, tracking=True, copy=False)
    receive_applications_count = fields.Integer(string="Nhận hồ sơ", compute="_compute_count_applicant", store=True,
                                     help="Số lượng hồ sơ ứng viên nộp hồ sơ")
    plan_id = fields.Many2one('ngsc.recruitment.plan', "Kế hoạch tuyển dụng", required=True, index=True)
    priority = fields.Selection(string='Mức độ ưu tiên', required=True, related='plan_id.priority')
    date = fields.Date(string='SLA tuyển dụng', required=True, related='plan_id.date')

    @api.depends("name")
    def _compute_short_name(self):
        for rec in self:
            rec.short_name = unicodedata.normalize('NFD', rec.name.replace("đ","d").replace("Đ","D"))\
        .encode('ascii','ignore').decode('utf-8').lower().replace(" ", "-")

    def _compute_website_url(self):
        web_base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        for rec in self:
            rec.website_url = f"/news-jobs/detail/{rec.short_name or ''}"
            rec.news_job_url = f"{web_base_url}/news-jobs/detail/{rec.short_name or ''}"

    def _compute_is_favorite(self):
        for job in self:
            job.is_favorite = self.env.user in job.favorite_user_ids

    def _inverse_is_favorite(self):
        unfavorited_news_jobs = favorite_news_jobs = self.env["ngsc.news.job"]
        for job in self:
            if self.env.user in job.favorite_user_ids:
                unfavorited_news_jobs |= job
            else:
                favorite_news_jobs |= job
        favorite_news_jobs.write({'favorite_user_ids': [(4, self.env.uid)]})
        unfavorited_news_jobs.write({'favorite_user_ids': [(3, self.env.uid)]})

    @api.depends("hr_applicant_ids", "hr_applicant_ids.stage_id")
    def _compute_count_applicant(self):
        for rec in self:
            applicants = rec.sudo().hr_applicant_ids
            rec.appraisal_count = len(applicants.filtered(lambda x: x.stage_id.state_type == "appraisal"))
            rec.interview_count = len(applicants.filtered(lambda x: x.stage_id.state_type == "interview"))
            rec.contract_proposal_count = len(
                applicants.filtered(lambda x: x.stage_id.state_type == "contract_proposal"))
            rec.contract_signed_count = len(applicants.filtered(lambda x: x.stage_id.state_type == "contract_signed"))
            rec.receive_applications_count = len(
                applicants.filtered(lambda x: x.stage_id.state_type == "receive_applications"))

    @api.depends('hr_applicant_ids.date_closed')
    def _compute_no_of_hired_employee(self):
        for rec in self:
            rec.no_of_hired_employee = len(rec.hr_applicant_ids.filtered(lambda x: x.date_closed))

    def _compute_all_application_count(self):
        read_group_result = self.env['hr.applicant'].with_context(active_test=False).read_group(
            [('news_job_id', 'in', self.ids)], ['news_job_id'], ['news_job_id'])
        result = dict((data['news_job_id'][0], data['news_job_id_count']) for data in read_group_result)
        for rec in self:
            rec.all_application_count = result.get(rec.id, 0)

    def _compute_application_count(self):
        read_group_result = self.env['hr.applicant'].read_group([('news_job_id', 'in', self.ids)], ['news_job_id'],
                                                                ['news_job_id'])
        result = dict((data['news_job_id'][0], data['news_job_id_count']) for data in read_group_result)
        for rec in self:
            rec.application_count = result.get(rec.id, 0)

    def _compute_state_new_application_count(self):
        for rec in self:
            rec.new_application_count = rec.receive_applications_count

    def _compute_new_application_count(self):
        self.env.cr.execute("""
            WITH job_stage AS (
                SELECT DISTINCT
                    ON (j.id) j.id AS news_job_id,
                           j.job_id AS job_id,
                           s.id AS stage_id,
                           s.sequence AS sequence
                FROM ngsc_news_job j
                LEFT JOIN hr_job_hr_recruitment_stage_rel rel
                    ON rel.hr_job_id = j.job_id
                JOIN hr_recruitment_stage s
                    ON s.id = rel.hr_recruitment_stage_id
                       OR s.id NOT IN (
                           SELECT hr_recruitment_stage_id
                           FROM hr_job_hr_recruitment_stage_rel
                           WHERE hr_recruitment_stage_id IS NOT NULL
                       )
                WHERE j.id IN %s
                ORDER BY 1, 4 ASC
            )
            SELECT s.news_job_id, COUNT(a.id) AS new_applicant
            FROM hr_applicant a
            JOIN job_stage s
                ON s.job_id = a.job_id
                AND a.stage_id = s.stage_id
                AND a.news_job_id = s.news_job_id
                AND a.active IS TRUE
            WHERE a.company_id IN %s
            GROUP BY s.news_job_id
        """, [tuple(self.ids), tuple(self.env.companies.ids)])

        new_applicant_count = dict(self.env.cr.fetchall())
        for job in self:
            job.new_application_count = new_applicant_count.get(job.id, 0)

    @api.depends('application_count', 'new_application_count')
    def _compute_old_application_count(self):
        for job in self:
            job.old_application_count = job.application_count - job.new_application_count

    def set_recruit(self):
        for record in self:
            no_of_recruitment = 1 if record.no_of_recruitment == 0 else record.no_of_recruitment
            record.write({
                'state': 'recruit',
                'no_of_recruitment': no_of_recruitment
            })
        return True

    def set_open(self):
        return self.write({
            'state': 'open',
            'no_of_recruitment': 0,
            'no_of_hired_employee': 0
        })

    @api.constrains("is_published")
    def _update_datetime_published(self):
        now = fields.Datetime.now()
        for rec in self:
            if not rec.is_published: continue
            rec.datetime_published = now

    @api.constrains("date_start", "date_end")
    def _check_date_start_date_end(self):
        for rec in self:
            if not rec.date_start or not rec.date_end: continue
            if rec.date_start > rec.date_end:
                raise ValidationError("Ngày bắt đầu tuyển không được lớn hơn Ngày kết thúc tuyển.")

