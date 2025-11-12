# -*- coding: utf-8 -*-
import logging

from odoo.http import request

from odoo import http, fields, exceptions

_logger = logging.getLogger(__name__)


class HrAttendanceController(http.Controller):
    @http.route('/hr_attendance_async/log', type='json', auth='user', methods=['POST'], csrf=False)
    def create_log(self, **data):
        try:
            employee_id = data.get('employee_id')
            action = data.get('action')  # 'check_in' or 'check_out'
            timestamp = data.get('timestamp') or fields.Datetime.now()

            if not employee_id or action not in ('check_in', 'check_out'):
                return {'error': 'missing_params'}

            vals = {
                'employee_id': int(employee_id),
                'action': action,
                'timestamp': timestamp,
            }
            rec = request.env['hr.attendance.log'].sudo().create(vals)
            return {'result': 'ok', 'id': rec.id}
        except exceptions.ValidationError as e:
            return {'error': 'validation', 'message': str(e)}
        except Exception as e:
            _logger.exception("Error creating attendance log: %s", e)
            return {'error': 'server_error', 'message': str(e)}
