# -*- coding: utf-8 -*-
import base64
from odoo import http, SUPERUSER_ID
from odoo import http, _
from odoo.http import request
from odoo.exceptions import AccessError, MissingError, ValidationError
from odoo.addons.website.controllers.form import WebsiteForm
from odoo.addons.base.models.ir_qweb_fields import nl2br


class NewsJobRecruitment(http.Controller):

    @http.route(['/news-jobs'], type='http', auth="public", website=True, sitemap=True)
    def news_jobs(self, **kwargs):
        news_jobs = request.env["ngsc.news.job"].sudo().search([("is_published", "=", True)])
        return request.render("ngsc_recruitment.news_job_list", {
            'news_jobs': news_jobs,
        })

    @http.route(['/news-jobs/detail/<string:short_name>'], type='http', auth="public", website=True, sitemap=True)
    def new_jobs_detail(self, short_name, **kwargs):
        news_job = request.env["ngsc.news.job"].sudo().search(
            [("short_name", "=", short_name), ("is_published", "=", True)], limit=1)
        if not news_job.is_published or not news_job.active:
            return request.render("website.page_404")
        return request.render("ngsc_recruitment.news_job_details", {
            'news_job': news_job
        })

    @http.route(['/news-jobs/apply/<string:short_name>'], type='http', auth="public", website=True, sitemap=True)
    def news_jobs_apply(self, short_name, **kwargs):
        news_job = request.env["ngsc.news.job"].sudo().search(
            [("short_name", "=", short_name), ("is_published", "=", True)], limit=1)
        if not news_job.is_published or not news_job.active:
            return request.render("website.page_404")
        error = {}
        default = {}
        if 'website_hr_recruitment_error' in request.session:
            error = request.session.pop('website_hr_recruitment_error')
            default = request.session.pop('website_hr_recruitment_default')
        return request.render("ngsc_recruitment.news_job_apply", {
            'news_job': news_job,
            'error': error,
            'default': default,
        })

    @http.route('/news-job-thank-you', type='http', auth='public', website=True, sitemap=True)
    def news_job_thank_you(self, **kwargs):
        return request.render('ngsc_recruitment.news_job_thank_you')


class WebsiteFormInherit(WebsiteForm):

    # Lưu CV ứng tuyển vào fields resume
    def insert_attachment(self, model, id_record, files):
        model_name = model.sudo().model
        record = model.env[model_name].browse(id_record)
        if model_name == "hr.applicant" and record.news_job_id:
            for file in files:
                name = file.filename
                datas = base64.encodebytes(file.read())
                record.write({"filename": name, "resume": datas})
        else:
            super().insert_attachment(model, id_record, files)
