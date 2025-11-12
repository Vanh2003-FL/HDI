from odoo import http
from odoo.http import request


class ProjectQualityDashboard(http.Controller):
    # api create dữ lieu báo cáo
    @http.route('/project/generate_report', type='json', auth='user', methods=['POST'], csrf=False)
    def generate_project_report(self, **kwargs):
        start_month = kwargs.get('start_month')
        end_month = kwargs.get('end_month')
        project_code = kwargs.get('project_code')

        try:
            request.env['project.quality.monthly.report'].sudo().generate_monthly_report(
                start_month=start_month,
                end_month=end_month,
                project_code=project_code
            )
            return {
                'status': 'success',
                'message': f'Generated report from {start_month or "current month"} to {end_month or start_month or "current month"}.'
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e),
            }

    # api create dữ lieu báo cáo cuối dự án
    @http.route('/project_completion/generate_report', type='json', auth='user', methods=['POST'], csrf=False)
    def generate_project_report_v2(self, **kwargs):
        project_code = kwargs.get('project_code'),
        start_month = kwargs.get('start_month')
        try:
            request.env['project.completion.quality.report'].sudo().generate_final_project_report(
                project_code=project_code,
                start_month=start_month,
            )
            return {
                'status': 'success',
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e),
            }
