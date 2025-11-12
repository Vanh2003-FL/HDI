from odoo import api, fields, SUPERUSER_ID
from datetime import timedelta


def run_first_quality_report(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    # Gọi hàm tạo báo cáo lần đầu
    env['project.quality.monthly.report'].generate_monthly_report()
    env['project.completion.quality.report'].generate_final_project_report()

    # Tìm cron và cập nhật lại nextcall = hôm nay 23h hoặc mai 23h nếu đã quá giờ
    cron = env.ref('ngsc_reporting.ir_cron_generate_quality_report', raise_if_not_found=False)
    cron_report = env.ref('ngsc_reporting.ir_cron_generate_project_completion_quality_report', raise_if_not_found=False)
    if cron:
        now = fields.Datetime.now()
        next_run = now.replace(hour=6, minute=0, second=0, microsecond=0)
        if now > next_run:
            next_run += timedelta(days=1)
        cron.write({
            'nextcall': next_run,
            'active': True,
        })

    if cron_report:
        now = fields.Datetime.now()
        next_run = now.replace(hour=23, minute=30, second=0, microsecond=0)
        if now > next_run:
            next_run += timedelta(days=1)
        cron_report.write({
            'nextcall': next_run,
            'active': True,
        })
